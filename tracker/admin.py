from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Project, TimeEntry, Tag
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
    list_display = ('nome', 'responsabile')
    filter_horizontal = ('tags',)


class TimeEntryAdmin(admin.ModelAdmin):
    def tags_display(self, obj):
        return ", ".join([t.nome for t in obj.tags.all()])
    tags_display.short_description = 'Tags'
    list_display = ('utente', 'progetto', 'inizio', 'fine', 'tipo_ticket', 'tags_display')
    filter_horizontal = ('tags',)
    readonly_fields = ('tipo_ticket',)
    actions = ['export_as_csv']

    def export_as_csv(self, request, queryset):
        """Export selected TimeEntry rows as a CSV file."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="time_entries.csv"'
        writer = csv.writer(response)
        writer.writerow(['id', 'user', 'user_email', 'project', 'start', 'end', 'duration_seconds', 'duration_hm', 'tags', 'description', 'tipo_ticket'])
        for e in queryset:
            tags = ", ".join([t.nome for t in e.tags.all()])
            start = e.inizio.isoformat() if e.inizio else ''
            end = e.fine.isoformat() if e.fine else ''
            try:
                dur_seconds = int((e.fine - e.inizio).total_seconds()) if e.fine else int((timezone.now() - e.inizio).total_seconds())
            except Exception:
                dur_seconds = ''
            duration_hm = ''
            if isinstance(dur_seconds, int) or isinstance(dur_seconds, float):
                h = dur_seconds // 3600
                m = (dur_seconds % 3600) // 60
                duration_hm = f"{h}h {m}m"
            writer.writerow([e.id, str(e.utente), getattr(e.utente, 'email', ''), e.progetto.nome if e.progetto else '', start, end, dur_seconds, duration_hm, tags, getattr(e, 'descrizione', '') or '', e.tipo_ticket or ''])
        return response
    export_as_csv.short_description = 'Export selected TimeEntry as CSV'


admin.site.register(User, UserAdmin)
class TagAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ore')
    search_fields = ('nome',)

admin.site.register(Tag, TagAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(TimeEntry, TimeEntryAdmin)
