from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'tracker'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('api/toggle/', views.toggle_ajax, name='api_toggle'),
    path('api/tag_create/', views.create_tag_ajax, name='api_tag_create'),
    path('api/csrf/', views.api_csrf, name='api_csrf'),
    path('api/login/', views.api_login, name='api_login'),
    path('api/logout/', views.api_logout, name='api_logout'),
    path('api/projects/', views.api_projects, name='api_projects'),
    path('api/tags/', views.api_tags, name='api_tags'),
    path('api/entries/', views.api_entries, name='api_entries'),
    path('api/add_entry/', views.api_add_entry, name='api_add_entry'),
]
