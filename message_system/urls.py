# core/message_system/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .api import MessageOpenViewSet

router = DefaultRouter()
router.register(r"message-opens", MessageOpenViewSet, basename="message-open")

app_name = 'message_system'

urlpatterns = [
    # Public tracking pixel (write-only)
    path("t/<uuid:uuid>.png", views.message_beacon, name="message_beacon"),
    
    # ========== IMPORTANT: Public Unsubscribe (must match email link) ==========
    # This path MUST match exactly what's in campaigns/tasks.py
    path("contacts/<int:pk>/unsubscribe/", views.PublicUnsubscribeView.as_view(), name="public_unsubscribe"),
    # ========================================================================
    
    # Contact Management URLs
    # These will be under /api/messages/ (from core urls.py)
    path("contacts/", views.ContactListView.as_view(), name="contact_list"),
    path("contacts/create/", views.ContactCreateView.as_view(), name="contact_create"),
    path("contacts/<int:pk>/", views.ContactDetailView.as_view(), name="contact_detail"),
    path("contacts/<int:pk>/edit/", views.ContactUpdateView.as_view(), name="contact_edit"),
    path("contacts/<int:pk>/delete/", views.ContactDeleteView.as_view(), name="contact_delete"),
    
    # Contact Status Management URLs
    path("contacts/<int:pk>/admin-unsubscribe/", views.ContactUnsubscribeView.as_view(), name="contact_unsubscribe"),
    path("contacts/<int:pk>/resubscribe/", views.ContactResubscribeView.as_view(), name="contact_resubscribe"),
    path("contacts/<int:pk>/activate/", views.ContactActivateView.as_view(), name="contact_activate"),
    path("contacts/<int:pk>/deactivate/", views.ContactDeactivateView.as_view(), name="contact_deactivate"),
    
    # Contact Import & Bulk Actions
    path("contacts/import/", views.ContactImportView.as_view(), name="contact_import"),
    path("contacts/bulk-action/", views.ContactBulkActionView.as_view(), name="contact_bulk_action"),
    
    # Contact Group Management URLs
    path("groups/", views.ContactGroupListView.as_view(), name="contactgroup_list"),
    path("groups/create/", views.ContactGroupCreateView.as_view(), name="contactgroup_create"),
    path("groups/<int:pk>/", views.ContactGroupDetailView.as_view(), name="contactgroup_detail"),
    path("groups/<int:pk>/edit/", views.ContactGroupUpdateView.as_view(), name="contactgroup_edit"),
    path("groups/<int:pk>/delete/", views.ContactGroupDeleteView.as_view(), name="contactgroup_delete"),
    path("groups/<int:pk>/update-members/", views.ContactGroupUpdateMembersView.as_view(), 
         name="contactgroup_update_members"),
    
    # API/JSON endpoints
    path("contacts/autocomplete/", views.ContactAutocompleteView.as_view(), name="contact_autocomplete"),
    path("contacts/stats/", views.ContactStatsView.as_view(), name="contact_stats"),
    
    # REST API endpoints (DRF)
    path("api/", include(router.urls)),
]