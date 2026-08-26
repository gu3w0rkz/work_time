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

    entries = TimeEntry.objects.filter(user=request.user).order_by('-start')[:50]
    # show projects and tags created by superuser(s)
    projects = Project.objects.filter(owner__is_superuser=True)
    tags = Tag.objects.filter(owner__is_superuser=True)
    open_entry = TimeEntry.objects.filter(user=request.user, end__isnull=True).first()
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
    open_entry = TimeEntry.objects.filter(user=user, end__isnull=True).first()
    if open_entry:
        open_entry.end = timezone.now()
        open_entry.save()
        return JsonResponse({'status': 'stopped', 'id': open_entry.id, 'end': open_entry.end.isoformat()})
    else:
        project_id = request.POST.get('project')
        # only allow selecting projects created by superuser
        project = Project.objects.filter(id=project_id, owner__is_superuser=True).first() if project_id else None
        entry = TimeEntry.objects.create(user=user, project=project, start=timezone.now())
        # handle tags (multiple)
        tag_ids = request.POST.getlist('tags')
        if tag_ids:
            # accept only tags created by superuser
            tags = Tag.objects.filter(id__in=tag_ids, owner__is_superuser=True)
            entry.tags.set(tags)
        return JsonResponse({'status': 'started', 'id': entry.id, 'start': entry.start.isoformat()})


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
    tag, created = Tag.objects.get_or_create(owner=request.user, name=name)
    return JsonResponse({'id': tag.id, 'name': tag.name, 'created': created})


def api_csrf(request):
    # returns csrf token and sets cookie
    token = get_token(request)
    return JsonResponse({'csrfToken': token})


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
    qs = Project.objects.filter(owner=request.user)
    data = [{'id': p.id, 'name': p.name} for p in qs]
    return JsonResponse({'projects': data})


def api_tags(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'unauthenticated'}, status=403)
    qs = Tag.objects.filter(owner=request.user)
    data = [{'id': t.id, 'name': t.name} for t in qs]
    return JsonResponse({'tags': data})


def api_entries(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'unauthenticated'}, status=403)
    qs = TimeEntry.objects.filter(user=request.user).order_by('-start')[:50]
    data = []
    for e in qs:
        data.append({
            'id': e.id,
            'project': e.project.name if e.project else None,
            'start': e.start.isoformat(),
            'end': e.end.isoformat() if e.end else None,
            'tags': [t.name for t in e.tags.all()],
        })
    return JsonResponse({'entries': data})


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
    project = Project.objects.filter(id=project_id, owner__is_superuser=True).first() if project_id else None

    # validate tag (only superuser-created tags allowed)
    tag = Tag.objects.filter(id=tag_id, owner__is_superuser=True).first() if tag_id else None

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
        try:
            start_dt = datetime.datetime.fromisoformat(start_iso)
            end_dt = datetime.datetime.fromisoformat(end_iso)
        except Exception:
            return JsonResponse({'error': 'invalid datetime format'}, status=400)
        duration = end_dt - start_dt
    else:
        start_dt = datetime.datetime.combine(d, dtime.min)
        duration = timedelta(hours=hours, minutes=minutes)
        end_dt = start_dt + duration

    entry = TimeEntry.objects.create(user=request.user, project=project, description=description, start=start_dt, end=end_dt)
    # set tags: prefer list 'tags' if present
    if tag_ids:
        tags_qs = Tag.objects.filter(id__in=tag_ids, owner__is_superuser=True)
        entry.tags.set(tags_qs)
    elif tag:
        entry.tags.set([tag])
    return JsonResponse({'ok': True, 'id': entry.id})
