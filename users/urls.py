# users/urls.py
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Index/Home page (public)
    path('', views.index, name='index'),
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard and Profile (authenticated only)
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('profile/', views.ProfileEditView.as_view(), name='profile_edit'),  # CORRECT: profile_edit with underscore
]