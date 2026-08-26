from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Project, TimeEntry, Tag


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
    list_display = ('user', 'project', 'start', 'end')
    filter_horizontal = ('tags',)


admin.site.register(User, UserAdmin)
admin.site.register(Tag)
admin.site.register(Project, ProjectAdmin)
admin.site.register(TimeEntry, TimeEntryAdmin)
