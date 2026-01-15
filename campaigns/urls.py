# campaigns/urls.py
from django.urls import path
from . import views

app_name = 'campaigns'

urlpatterns = [
    path('', views.CampaignListView.as_view(), name='list'),
    path('create/', views.CampaignCreateView.as_view(), name='create'),
    path('<int:pk>/', views.CampaignDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.CampaignUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.CampaignDeleteView.as_view(), name='delete'),
    path('<int:pk>/duplicate/', views.CampaignDuplicateView.as_view(), name='duplicate'),
    path('<int:pk>/toggle/', views.CampaignToggleStatusView.as_view(), name='toggle'),
    path('<int:pk>/send-now/', views.CampaignSendNowView.as_view(), name='send_now'),
    path('<int:pk>/pause/', views.CampaignPauseView.as_view(), name='pause'),
    path('<int:pk>/resume/', views.CampaignResumeView.as_view(), name='resume'),
]