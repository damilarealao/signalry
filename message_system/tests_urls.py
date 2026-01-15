# message_system/tests_urls.py
from django.test import TestCase
from django.urls import reverse, resolve
from . import views


class URLTests(TestCase):
    """Test that URLs resolve to correct views."""
    
    def test_contact_list_url(self):
        url = reverse('message_system:contact_list')
        self.assertEqual(resolve(url).func.view_class, views.ContactListView)

    def test_contact_create_url(self):
        url = reverse('message_system:contact_create')
        self.assertEqual(resolve(url).func.view_class, views.ContactCreateView)

    def test_contact_detail_url(self):
        url = reverse('message_system:contact_detail', args=[1])
        self.assertEqual(resolve(url).func.view_class, views.ContactDetailView)

    def test_contact_edit_url(self):
        url = reverse('message_system:contact_edit', args=[1])
        self.assertEqual(resolve(url).func.view_class, views.ContactUpdateView)

    def test_contact_delete_url(self):
        url = reverse('message_system:contact_delete', args=[1])
        self.assertEqual(resolve(url).func.view_class, views.ContactDeleteView)

    def test_contact_import_url(self):
        url = reverse('message_system:contact_import')
        self.assertEqual(resolve(url).func.view_class, views.ContactImportView)

    def test_contact_bulk_action_url(self):
        url = reverse('message_system:contact_bulk_action')
        self.assertEqual(resolve(url).func.view_class, views.ContactBulkActionView)

    def test_group_list_url(self):
        url = reverse('message_system:contactgroup_list')
        self.assertEqual(resolve(url).func.view_class, views.ContactGroupListView)

    def test_group_create_url(self):
        url = reverse('message_system:contactgroup_create')
        self.assertEqual(resolve(url).func.view_class, views.ContactGroupCreateView)

    def test_group_detail_url(self):
        url = reverse('message_system:contactgroup_detail', args=[1])
        self.assertEqual(resolve(url).func.view_class, views.ContactGroupDetailView)

    def test_group_edit_url(self):
        url = reverse('message_system:contactgroup_edit', args=[1])
        self.assertEqual(resolve(url).func.view_class, views.ContactGroupUpdateView)

    def test_group_delete_url(self):
        url = reverse('message_system:contactgroup_delete', args=[1])
        self.assertEqual(resolve(url).func.view_class, views.ContactGroupDeleteView)

    def test_group_update_members_url(self):
        url = reverse('message_system:contactgroup_update_members', args=[1])
        self.assertEqual(resolve(url).func.view_class, views.ContactGroupUpdateMembersView)

    def test_beacon_url(self):
        url = reverse('message_system:message_beacon', args=['12345678-1234-5678-1234-567812345678'])
        self.assertEqual(resolve(url).func, views.message_beacon)