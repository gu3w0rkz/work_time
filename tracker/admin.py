from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Project, TimeEntry, Tag, PALETTE
from django import forms
from django.utils.html import format_html, mark_safe
from django.utils import timezone
import csv
from django.http import HttpResponse


class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ('email', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('email',)
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active')
        }),
    )

class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner')
    filter_horizontal = ('tags',)


class TimeEntryAdmin(admin.ModelAdmin):
    def tags_display(self, obj):
        return ", ".join([t.name for t in obj.tags.all()])
    tags_display.short_description = 'Tags'

    list_display = ('user', 'project', 'start', 'end', 'jira_issue_type', 'tags_display')
    filter_horizontal = ('tags',)
    readonly_fields = ('jira_issue_type',)
    actions = ['export_as_csv']

    def export_as_csv(self, request, queryset):
        """Export selected TimeEntry rows as a CSV file."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="time_entries.csv"'
        writer = csv.writer(response)
        writer.writerow(['id', 'user', 'user_email', 'project', 'start', 'end', 'duration_seconds', 'duration_hm', 'tags', 'description', 'jira_issue_type'])
        for e in queryset:
            tags = ", ".join([t.name for t in e.tags.all()])
            start = e.start.isoformat() if e.start else ''
            end = e.end.isoformat() if e.end else ''
            try:
                dur_seconds = int((e.end - e.start).total_seconds()) if e.end else int((timezone.now() - e.start).total_seconds())
            except Exception:
                dur_seconds = ''
            duration_hm = ''
            if isinstance(dur_seconds, int) or isinstance(dur_seconds, float):
                h = dur_seconds // 3600
                m = (dur_seconds % 3600) // 60
                duration_hm = f"{h}h {m}m"
            writer.writerow([e.id, str(e.user), getattr(e.user, 'email', ''), e.project.name if e.project else '', start, end, dur_seconds, duration_hm, tags, e.description or '', e.jira_issue_type or ''])
        return response
    export_as_csv.short_description = 'Export selected TimeEntry as CSV'


admin.site.register(User, UserAdmin)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'hours', 'color', 'color_preview')
    search_fields = ('name',)

    def color_preview(self, obj):
        c = obj.color or obj.get_color()
        if isinstance(c, dict):
            bg = c.get('bg')
            border = c.get('border')
        else:
            bg = c
            border = c
        return format_html('<div style="width:32px;height:16px;border-radius:4px;background:{};border:2px solid {}"></div>', bg, border)
    color_preview.short_description = 'Preview'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # present a simple palette of light background colors as radio choices
        # build HTML labels so each radio shows a colored swatch and the hex text
        choices = []
        for c in PALETTE:
            label_html = f'<span style="display:block;width:44px;height:18px;border-radius:6px;background:{c};border:2px solid rgba(0,0,0,0.08);"></span><span class="hex">{c}</span>'
            choices.append((c, mark_safe(label_html)))
        form.base_fields['color'] = forms.ChoiceField(choices=choices, required=False, widget=forms.RadioSelect(attrs={'class': 'palette-radio'}))
        # if object has color as dict, normalize to bg hex
        if obj and obj.color and isinstance(obj.color, dict):
            form.base_fields['color'].initial = obj.color.get('bg')
        return form

    class Media:
        css = {
            'all': ('/static/tracker/admin_tag_palette.css',)
        }
        

admin.site.register(Tag, TagAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(TimeEntry, TimeEntryAdmin)
