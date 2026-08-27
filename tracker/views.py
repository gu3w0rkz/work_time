from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.utils import timezone
from django.http import JsonResponse
from .models import TimeEntry, Project, Tag
import datetime
from datetime import time as dtime, timedelta
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_POST
from django.middleware.csrf import get_token
from django.core import serializers
from django.forms.models import model_to_dict
import requests
import logging
from django.conf import settings
from django.utils import translation

logger = logging.getLogger(__name__)

class LoginView(auth_views.LoginView):
    template_name = 'tracker/login.html'

def logout_view(request):
    return auth_views.LogoutView.as_view(next_page='tracker:login')(request)

@login_required
def dashboard(request):
    # Only superuser (admin) should create projects/tags via Django admin.
    # For dashboard we show projects and tags created by the superuser.
    if request.method == 'POST':
        # Keep POST handling minimal; creation of projects/tags should be done by admin in /admin/
        return redirect('tracker:dashboard')

    entries = TimeEntry.objects.filter(utente=request.user).order_by('-inizio')[:50]
    # show projects and tags created by superuser(s)
    projects = Project.objects.filter(responsabile__is_superuser=True)
    tags = Tag.objects.all()
    open_entry = TimeEntry.objects.filter(utente=request.user, fine__isnull=True).first()
    return render(request, 'tracker/dashboard.html', {
        'entries': entries,
        'projects': projects,
        'tags': tags,
        'open_entry': open_entry,
    })


@login_required
def toggle_ajax(request):
    # expects POST, toggles start/stop and returns JSON
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)
    user = request.user
    open_entry = TimeEntry.objects.filter(utente=user, fine__isnull=True).first()
    if open_entry:
        open_entry.fine = timezone.now()
        open_entry.save()
        return JsonResponse({'status': 'stopped', 'id': open_entry.id, 'end': open_entry.fine.isoformat()})
    else:
        project_id = request.POST.get('project')
        # only allow selecting projects created by superuser
        project = Project.objects.filter(id=project_id, responsabile__is_superuser=True).first() if project_id else None
        entry = TimeEntry.objects.create(utente=user, progetto=project, inizio=timezone.now())
        # handle tags (multiple)
        tag_ids = request.POST.getlist('tags')
        if tag_ids:
            # accept only existing tags (creation reserved to admin)
            tags = Tag.objects.filter(id__in=tag_ids)
            entry.tags.set(tags)
        return JsonResponse({'status': 'started', 'id': entry.id, 'start': entry.inizio.isoformat()})


@login_required
def create_tag_ajax(request):
    # Tag creation must be done by superuser via Django admin. Protect this endpoint.
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({'error': 'forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'missing name'}, status=400)
    tag, created = Tag.objects.get_or_create(nome=name)
    return JsonResponse({'id': tag.id, 'name': tag.nome, 'created': created})


def api_csrf(request):
    # returns csrf token and sets cookie
    token = get_token(request)
    return JsonResponse({'csrfToken': token})


def api_get_language(request):
    # return current language code
    lang = getattr(request, 'LANGUAGE_CODE', None) or request.session.get('django_language') or settings.LANGUAGE_CODE
    return JsonResponse({'language': lang})


@require_POST
def api_set_language(request):
    lang = request.POST.get('language')
    if not lang or lang not in dict(settings.LANGUAGES):
        return JsonResponse({'error': 'invalid_language'}, status=400)
    # store in session and activate for this request
    request.session['django_language'] = lang
    translation.activate(lang)
    return JsonResponse({'language': lang})


@require_POST
def api_login(request):
    email = request.POST.get('email') or request.POST.get('username')
    password = request.POST.get('password')
    user = authenticate(request, username=email, password=password)
    if user is not None:
        login(request, user)
        return JsonResponse({'ok': True, 'email': user.email})
    return JsonResponse({'ok': False, 'error': 'invalid_credentials'}, status=400)


@require_POST
def api_logout(request):
    logout(request)
    return JsonResponse({'ok': True})


def api_projects(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'unauthenticated'}, status=403)
    qs = Project.objects.filter(responsabile=request.user)
    data = [{'id': p.id, 'name': p.nome} for p in qs]
    return JsonResponse({'projects': data})


def api_tags(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'unauthenticated'}, status=403)
    qs = Tag.objects.all()
    data = []
    for t in qs:
        data.append({'id': t.id, 'name': t.nome})
    return JsonResponse({'tags': data})


def api_entries(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'unauthenticated'}, status=403)
    qs = TimeEntry.objects.filter(utente=request.user).order_by('-inizio')[:50]
    data = []
    for e in qs:
        data.append({
            'id': e.id,
            'project': e.progetto.nome if e.progetto else None,
            'jira_issue_type': e.tipo_ticket if hasattr(e, 'tipo_ticket') else None,
            'description': e.descrizione if hasattr(e, 'descrizione') else None,
            'start': e.inizio.isoformat(),
            'end': e.fine.isoformat() if e.fine else None,
            'tags': [{'id': t.id, 'name': t.nome} for t in e.tags.all()],
        })
    return JsonResponse({'entries': data})


@login_required
def api_jira_search(request):
    """Proxy endpoint to search Jira issues. Query params: q (text) or key (issue key).
    Returns JSON list of {key, summary}.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'unauthenticated'}, status=403)

    base = getattr(settings, 'JIRA_BASE_URL', None)
    email = getattr(settings, 'JIRA_EMAIL', None)
    token = getattr(settings, 'JIRA_API_TOKEN', None)
    if not base or not email or not token:
        return JsonResponse({'error': 'jira_not_configured'}, status=500)

    q = request.GET.get('q', '').strip()
    key = request.GET.get('key', '').strip()
    auth = (email, token)

    try:
        # if 'key' param provided use issue GET
        if key:
            url = f"{base.rstrip('/')}/rest/api/3/issue/{key}"
            r = requests.get(url, auth=auth, timeout=5)
            if r.status_code != 200:
                return JsonResponse({'error': 'not found', 'status': r.status_code}, status=404)
            js = r.json()
            itype = js.get('fields', {}).get('issuetype', {}) or {}
            return JsonResponse({'issues': [{'key': js.get('key'), 'summary': js.get('fields',{}).get('summary'), 'issuetype': itype.get('name')}]})

        # if q looks like an issue key (e.g. PROJ-123) do exact issue lookup
        import re
        if q and re.match(r'^[A-Za-z0-9]+-\d+$', q.strip()):
            issue_key = q.strip().upper()
            url = f"{base.rstrip('/')}/rest/api/3/issue/{issue_key}"
            r = requests.get(url, auth=auth, timeout=5)
            if r.status_code == 200:
                js = r.json()
                itype = js.get('fields', {}).get('issuetype', {}) or {}
                return JsonResponse({'issues': [{'key': js.get('key'), 'summary': js.get('fields',{}).get('summary'), 'issuetype': itype.get('name')} ]})
            else:
                return JsonResponse({'issues': []})

        if not q:
            return JsonResponse({'issues': []})

        # use new Jira API endpoint /rest/api/3/search/jql with POST payload
        # broaden search: issue key OR summary OR description; allow optional project filter
        project_filter = request.GET.get('project')
        jql_parts = [f'issuekey ~ "{q}"', f'summary ~ "{q}"', f'description ~ "{q}"']
        if project_filter:
            jql_parts.insert(0, f'project = "{project_filter}"')
        jql = ' OR '.join(jql_parts)
        url = f"{base.rstrip('/')}/rest/api/3/search/jql"
        payload = {'jql': jql, 'maxResults': 50, 'fields': ['summary', 'key', 'project', 'issuetype', 'labels']}
        headers = {'Content-Type': 'application/json'}
        r = requests.post(url, json=payload, auth=auth, headers=headers, timeout=8)
        if r.status_code != 200:
            body = r.text
            logger.error('Jira search (jql) failed %s %s', r.status_code, body[:1000])
            return JsonResponse({'error': 'jira_error', 'status': r.status_code, 'detail': body[:1000]}, status=502)
        js = r.json()
        issues = []
        for it in js.get('issues', []):
            f = it.get('fields', {})
            issuetype = (f.get('issuetype') or {}).get('name')
            issues.append({'key': it.get('key'), 'summary': f.get('summary'), 'issuetype': issuetype})
        return JsonResponse({'issues': issues})
    except Exception as e:
        return JsonResponse({'error': 'jira_exception', 'detail': str(e)}, status=500)


@login_required
def api_add_entry(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'unauthenticated'}, status=403)

    # expected fields: project (id), tag (id), description, date (YYYY-MM-DD), start, end, hours, minutes
    project_id = request.POST.get('project')
    # accept multiple tags via 'tags' or single 'tag'
    tag_id = request.POST.get('tag')
    tag_ids = request.POST.getlist('tags')
    description = request.POST.get('description', '').strip()
    date_str = request.POST.get('date')
    hours = int(request.POST.get('hours') or 0)
    minutes = int(request.POST.get('minutes') or 0)

    # validate project (only superuser-created projects allowed)
    project = Project.objects.filter(id=project_id, responsabile__is_superuser=True).first() if project_id else None

    # validate tag (only superuser-created tags allowed)
    tag = Tag.objects.filter(id=tag_id).first() if tag_id else None

    # parse date
    try:
        if date_str:
            d = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            d = datetime.datetime.now().date()
    except ValueError:
        return JsonResponse({'error': 'invalid_date'}, status=400)

    # prefer start/end ISO datetimes; fallback to hours/minutes duration
    start_iso = request.POST.get('start')
    end_iso = request.POST.get('end')
    if start_iso and end_iso:
        def parse_iso(s):
            # try fromisoformat, but accept trailing Z (UTC) and fallback to naive parse
            try:
                return datetime.datetime.fromisoformat(s)
            except Exception:
                # handle Zulu 'Z' suffix
                if isinstance(s, str) and s.endswith('Z'):
                    try:
                        return datetime.datetime.fromisoformat(s[:-1] + '+00:00')
                    except Exception:
                        pass
                # fallback: try without fractional seconds/timezone
                try:
                    return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S')
                except Exception:
                    raise

        try:
            start_dt = parse_iso(start_iso)
            end_dt = parse_iso(end_iso)
        except Exception:
            return JsonResponse({'error': 'invalid datetime format'}, status=400)

        # ensure timezone-aware datetimes in current timezone
        if start_dt.tzinfo is None:
            start_dt = timezone.make_aware(start_dt)
        else:
            start_dt = start_dt.astimezone(timezone.get_current_timezone())
        if end_dt.tzinfo is None:
            end_dt = timezone.make_aware(end_dt)
        else:
            end_dt = end_dt.astimezone(timezone.get_current_timezone())

        duration = end_dt - start_dt
    else:
        start_dt = datetime.datetime.combine(d, dtime.min)
        duration = timedelta(hours=hours, minutes=minutes)
        end_dt = start_dt + duration

    entry = TimeEntry.objects.create(utente=request.user, progetto=project, descrizione=description, inizio=start_dt, fine=end_dt)
    # optional jira issue type
    jira_issue_type = request.POST.get('jira_issue_type')
    if jira_issue_type:
        entry.tipo_ticket = jira_issue_type
        entry.save()
    # set tags: prefer list 'tags' if present
    if tag_ids:
        tags_qs = Tag.objects.filter(id__in=tag_ids)
        entry.tags.set(tags_qs)
    elif tag:
        entry.tags.set([tag])
    return JsonResponse({'ok': True, 'id': entry.id})


@login_required
@require_POST
def api_delete_entry(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'unauthenticated'}, status=403)
    entry_id = request.POST.get('id') or request.POST.get('entry')
    if not entry_id:
        return JsonResponse({'error': 'missing id'}, status=400)
    entry = TimeEntry.objects.filter(id=entry_id, utente=request.user).first()
    if not entry:
        return JsonResponse({'error': 'not found'}, status=404)
    entry.delete()
    return JsonResponse({'ok': True, 'id': entry_id})
