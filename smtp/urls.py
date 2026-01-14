# smtp/urls.py
from django.urls import path
from . import views

app_name = 'smtp'

urlpatterns = [
    path('', views.SMTPListView.as_view(), name='list'),
    path('add/', views.SMTPCreateView.as_view(), name='add'),
    path('<int:pk>/edit/', views.SMTPUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.SMTPDeleteView.as_view(), name='delete'),
    path('<int:pk>/test/', views.SMTPTestView.as_view(), name='test'),
    path('<int:pk>/toggle/', views.SMTPToggleStatusView.as_view(), name='toggle'),
]