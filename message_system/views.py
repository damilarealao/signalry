# core/message_system/views.py
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.db.models import Q
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import csv
import io
import json
import hashlib

from .models import Contact, ContactGroup, Message, MessageRecipient, MessageOpen
from .forms import ContactForm, ContactGroupForm, ContactImportForm

# Get logger
logger = logging.getLogger(__name__)


# -------------------- Contact Views --------------------
class ContactListView(LoginRequiredMixin, ListView):
    model = Contact
    template_name = 'core/message_system/contact_list.html'
    context_object_name = 'contacts'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Contact.objects.filter(user=self.request.user)
        
        # Filter by search query
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(company__icontains=search) |
                Q(tags__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by group
        group_id = self.request.GET.get('group', '')
        if group_id:
            try:
                group = ContactGroup.objects.get(id=group_id, user=self.request.user)
                queryset = queryset.filter(groups=group)
            except ContactGroup.DoesNotExist:
                pass
        
        # Ordering
        order_by = self.request.GET.get('order_by', '-created_at')
        if order_by.lstrip('-') in ['email', 'first_name', 'last_name', 'status', 'is_active', 'created_at']:
            queryset = queryset.order_by(order_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_contacts'] = Contact.objects.filter(user=self.request.user).count()
        context['status_choices'] = Contact.STATUS_CHOICES
        context['contact_groups'] = ContactGroup.objects.filter(user=self.request.user)
        
        # Add search/filter parameters to context
        context['current_search'] = self.request.GET.get('search', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_group'] = self.request.GET.get('group', '')
        context['current_order'] = self.request.GET.get('order_by', '-created_at')
        
        return context


class ContactDetailView(LoginRequiredMixin, DetailView):
    model = Contact
    template_name = 'core/message_system/contact_detail.html'
    context_object_name = 'contact'
    
    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get message history for this contact
        context['message_history'] = MessageRecipient.objects.filter(
            contact=self.object
        ).select_related('message', 'message__campaign').order_by('-created_at')[:10]
        
        # Get open/click statistics
        opens = MessageOpen.objects.filter(recipient__contact=self.object).count()
        clicks = 0  # You'll need to add click tracking if not already
        
        context['open_count'] = opens
        context['click_count'] = clicks
        context['groups'] = self.object.groups.all()
        
        # Get contacts from same company
        if self.object.company:
            context['company_contacts'] = Contact.objects.filter(
                user=self.request.user,
                company=self.object.company
            ).exclude(pk=self.object.pk)[:5]
        
        # Get tags as list
        if self.object.tags:
            context['tags_list'] = [tag.strip() for tag in self.object.tags.split(',')]
        
        return context


class ContactCreateView(LoginRequiredMixin, CreateView):
    model = Contact
    form_class = ContactForm
    template_name = 'core/message_system/contact_form.html'
    success_url = reverse_lazy('message_system:contact_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Contact "{self.object.email}" created successfully.')
        return response


class ContactUpdateView(LoginRequiredMixin, UpdateView):
    model = Contact
    form_class = ContactForm
    template_name = 'core/message_system/contact_form.html'
    
    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_success_url(self):
        return reverse_lazy('message_system:contact_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Contact "{self.object.email}" updated successfully.')
        return response


class ContactDeleteView(LoginRequiredMixin, DeleteView):
    model = Contact
    template_name = 'core/message_system/contact_confirm_delete.html'
    success_url = reverse_lazy('message_system:contact_list')
    
    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        email = self.object.email
        response = super().form_valid(form)
        messages.success(self.request, f'Contact "{email}" deleted successfully.')
        return response


class ContactUnsubscribeView(LoginRequiredMixin, View):
    """View to unsubscribe a contact (admin only)."""
    
    def post(self, request, pk, *args, **kwargs):
        contact = get_object_or_404(Contact, pk=pk, user=request.user)
        contact.unsubscribe()
        messages.success(request, f'Contact "{contact.email}" has been unsubscribed.')
        return redirect('message_system:contact_detail', pk=contact.pk)


class ContactResubscribeView(LoginRequiredMixin, View):
    """View to resubscribe a contact (admin only)."""
    
    def post(self, request, pk, *args, **kwargs):
        contact = get_object_or_404(Contact, pk=pk, user=request.user)
        contact.resubscribe()
        messages.success(request, f'Contact "{contact.email}" has been resubscribed.')
        return redirect('message_system:contact_detail', pk=contact.pk)


class ContactActivateView(LoginRequiredMixin, View):
    """View to activate a contact (set is_active=True)."""
    
    def post(self, request, pk, *args, **kwargs):
        contact = get_object_or_404(Contact, pk=pk, user=request.user)
        
        # Only activate if status is subscribed
        if contact.status != 'subscribed':
            messages.error(request, f'Cannot activate a contact with status "{contact.get_status_display()}". Only subscribed contacts can be activated.')
            return redirect('message_system:contact_detail', pk=contact.pk)
        
        contact.is_active = True
        contact.save(update_fields=['is_active', 'updated_at'])
        messages.success(request, f'Contact "{contact.email}" has been activated.')
        return redirect('message_system:contact_detail', pk=contact.pk)


class ContactDeactivateView(LoginRequiredMixin, View):
    """View to deactivate a contact (set is_active=False)."""
    
    def post(self, request, pk, *args, **kwargs):
        contact = get_object_or_404(Contact, pk=pk, user=request.user)
        
        # Only deactivate if status is subscribed
        if contact.status != 'subscribed':
            messages.error(request, f'Cannot deactivate a contact with status "{contact.get_status_display()}". Only subscribed contacts can be deactivated.')
            return redirect('message_system:contact_detail', pk=contact.pk)
        
        contact.is_active = False
        contact.save(update_fields=['is_active', 'updated_at'])
        messages.success(request, f'Contact "{contact.email}" has been deactivated.')
        return redirect('message_system:contact_detail', pk=contact.pk)


class PublicUnsubscribeView(View):
    """Public unsubscribe endpoint for email recipients (no authentication required)."""
    
    template_name = 'core/message_system/unsubscribe.html'
    
    def get(self, request, pk, *args, **kwargs):
        """Show unsubscribe confirmation page."""
        try:
            contact = Contact.objects.get(pk=pk)
            return render(request, self.template_name, {
                'contact': contact,
                'success': False,
                'error': None
            })
        except Contact.DoesNotExist:
            # Show error if contact doesn't exist
            return render(request, self.template_name, {
                'contact': None,
                'success': False,
                'error': 'Contact not found or already unsubscribed.'
            })
    
    def post(self, request, pk, *args, **kwargs):
        """Handle unsubscribe confirmation."""
        try:
            contact = Contact.objects.get(pk=pk)
            
            # Unsubscribe the contact
            contact.unsubscribe()
            
            # Log the unsubscribe for analytics
            logger.info(f"Contact {contact.email} (ID: {contact.pk}) unsubscribed via public link")
            
            return render(request, self.template_name, {
                'contact': contact,
                'success': True,
                'error': None
            })
            
        except Contact.DoesNotExist:
            return render(request, self.template_name, {
                'contact': None,
                'success': False,
                'error': 'Contact not found or already unsubscribed.'
            })


class ContactImportView(LoginRequiredMixin, TemplateView):
    template_name = 'core/message_system/contact_import.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ContactImportForm()
        return context
    
    def post(self, request, *args, **kwargs):
        form = ContactImportForm(request.POST, request.FILES)
        
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            
            try:
                success_count, error_count, errors = Contact.objects.bulk_create_from_csv(
                    user=request.user,
                    csv_file=csv_file
                )
                
                if success_count > 0:
                    messages.success(
                        request, 
                        f'Successfully imported {success_count} contacts. '
                        f'{error_count} errors occurred.'
                    )
                
                if errors:
                    for error in errors[:10]:  # Show first 10 errors
                        messages.warning(request, error)
                    
                    if len(errors) > 10:
                        messages.warning(
                            request, 
                            f'... and {len(errors) - 10} more errors.'
                        )
                
                if success_count == 0 and error_count > 0:
                    messages.error(request, 'No contacts were imported. Please check your CSV file.')
                
                return redirect('message_system:contact_list')
                
            except Exception as e:
                messages.error(request, f'Error importing contacts: {str(e)}')
        
        context = self.get_context_data(**kwargs)
        context['form'] = form
        return render(request, self.template_name, context)


class ContactBulkActionView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', '')
        contact_ids = request.POST.getlist('contact_ids', [])
        
        if not contact_ids:
            messages.error(request, 'No contacts selected.')
            return redirect('message_system:contact_list')
        
        contacts = Contact.objects.filter(
            id__in=contact_ids,
            user=request.user
        )
        
        if action == 'delete':
            count = contacts.count()
            contacts.delete()
            messages.success(request, f'Deleted {count} contacts.')
        
        elif action == 'unsubscribe':
            count = 0
            for contact in contacts:
                contact.unsubscribe()
                count += 1
            messages.success(request, f'Unsubscribed {count} contacts.')
        
        elif action == 'resubscribe':
            count = 0
            for contact in contacts:
                contact.resubscribe()
                count += 1
            messages.success(request, f'Resubscribed {count} contacts.')
        
        elif action == 'activate':
            count = 0
            for contact in contacts:
                if contact.status == 'subscribed':
                    contact.is_active = True
                    contact.save(update_fields=['is_active', 'updated_at'])
                    count += 1
            messages.success(request, f'Activated {count} contacts.')
        
        elif action == 'deactivate':
            count = 0
            for contact in contacts:
                if contact.status == 'subscribed':
                    contact.is_active = False
                    contact.save(update_fields=['is_active', 'updated_at'])
                    count += 1
            messages.success(request, f'Deactivated {count} contacts.')
        
        elif action == 'add_to_group':
            group_id = request.POST.get('group_id', '')
            try:
                group = ContactGroup.objects.get(id=group_id, user=request.user)
                for contact in contacts:
                    contact.groups.add(group)
                messages.success(request, f'Added {contacts.count()} contacts to group "{group.name}".')
            except ContactGroup.DoesNotExist:
                messages.error(request, 'Group not found.')
        
        elif action == 'remove_from_group':
            group_id = request.POST.get('group_id', '')
            try:
                group = ContactGroup.objects.get(id=group_id, user=request.user)
                for contact in contacts:
                    contact.groups.remove(group)
                messages.success(request, f'Removed {contacts.count()} contacts from group "{group.name}".')
            except ContactGroup.DoesNotExist:
                messages.error(request, 'Group not found.')
        
        else:
            messages.error(request, 'Invalid action.')
        
        return redirect('message_system:contact_list')


# -------------------- Contact Group Views --------------------
class ContactGroupListView(LoginRequiredMixin, ListView):
    model = ContactGroup
    template_name = 'core/message_system/contactgroup_list.html'
    context_object_name = 'groups'
    
    def get_queryset(self):
        return ContactGroup.objects.filter(user=self.request.user).prefetch_related('contacts')


class ContactGroupDetailView(LoginRequiredMixin, DetailView):
    model = ContactGroup
    template_name = 'core/message_system/contactgroup_detail.html'
    context_object_name = 'group'
    
    def get_queryset(self):
        return ContactGroup.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get contacts in this group
        if self.object.is_dynamic:
            contacts = self.object.get_contacts()
        else:
            contacts = self.object.contacts.all()
        
        # Paginate contacts
        from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
        
        page = self.request.GET.get('page', 1)
        paginator = Paginator(contacts, 20)
        
        try:
            contacts_page = paginator.page(page)
        except PageNotAnInteger:
            contacts_page = paginator.page(1)
        except EmptyPage:
            contacts_page = paginator.page(paginator.num_pages)
        
        context['contacts'] = contacts_page
        context['total_contacts'] = contacts.count()
        
        return context


class ContactGroupCreateView(LoginRequiredMixin, CreateView):
    model = ContactGroup
    form_class = ContactGroupForm
    template_name = 'core/message_system/contactgroup_form.html'
    success_url = reverse_lazy('message_system:contactgroup_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Group "{self.object.name}" created successfully.')
        
        # Update dynamic group membership if needed
        if self.object.is_dynamic:
            count = self.object.update_dynamic_members()
            messages.info(self.request, f'Group updated with {count} contacts.')
        
        return response


class ContactGroupUpdateView(LoginRequiredMixin, UpdateView):
    model = ContactGroup
    form_class = ContactGroupForm
    template_name = 'core/message_system/contactgroup_form.html'
    
    def get_queryset(self):
        return ContactGroup.objects.filter(user=self.request.user)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_success_url(self):
        return reverse_lazy('message_system:contactgroup_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Group "{self.object.name}" updated successfully.')
        
        # Update dynamic group membership if needed
        if self.object.is_dynamic:
            count = self.object.update_dynamic_members()
            messages.info(self.request, f'Group updated with {count} contacts.')
        
        return response


class ContactGroupDeleteView(LoginRequiredMixin, DeleteView):
    model = ContactGroup
    template_name = 'core/message_system/contactgroup_confirm_delete.html'
    success_url = reverse_lazy('message_system:contactgroup_list')
    
    def get_queryset(self):
        return ContactGroup.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        name = self.object.name
        response = super().form_valid(form)
        messages.success(self.request, f'Group "{name}" deleted successfully.')
        return response


class ContactGroupUpdateMembersView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        group = get_object_or_404(ContactGroup, pk=pk, user=request.user)
        
        if group.is_dynamic:
            count = group.update_dynamic_members()
            messages.success(request, f'Updated dynamic group with {count} contacts.')
        else:
            messages.info(request, 'This is a static group. Members must be added manually.')
        
        return redirect('message_system:contactgroup_detail', pk=group.pk)


# -------------------- Tracking Beacon View --------------------

# 1x1 transparent PNG
PIXEL = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4"
    b"\x89\x00\x00\x00\nIDATx\xdac\xf8"
    b"\x0f\x00\x01\x01\x01\x00\x18\xdd"
    b"\x8d\x18\x00\x00\x00\x00IEND\xaeB`\x82"
)

@csrf_exempt
@require_GET
def message_beacon(request, uuid):
    """
    Tracking pixel endpoint.
    Public, write-only, privacy-safe.
    """
    try:
        # Try to get message by UUID
        message = Message.objects.get(uuid=uuid)
        
        # Get raw IP and user agent
        raw_ip = request.META.get("REMOTE_ADDR", "")
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        
        # Get recipient ID from query parameters
        recipient_id = request.GET.get('recipient', '')
        recipient = None
        
        if recipient_id:
            try:
                recipient = MessageRecipient.objects.get(id=recipient_id, message=message)
                logger.info(f"Tracking pixel hit for recipient {recipient_id}, message {message.id}")
            except MessageRecipient.DoesNotExist:
                logger.warning(f"Recipient {recipient_id} not found for message {message.id}")
                recipient = None
        
        # Hash IP for privacy (optional)
        ip_hash = None
        if raw_ip:
            ip_hash = hashlib.sha256(raw_ip.encode("utf-8")).hexdigest()
        
        # Extract user agent family (browser/device type)
        user_agent_family = ""
        if user_agent:
            # Simple extraction - just get the first part
            parts = user_agent.split('/')
            if parts:
                user_agent_family = parts[0][:50]
        
        # Create MessageOpen record
        MessageOpen.objects.create(
            message=message,
            recipient=recipient,
            beacon_uuid=str(uuid),
            ip_hash=ip_hash,
            user_agent_family=user_agent_family
        )
        
        # Update recipient status if found
        if recipient:
            recipient.mark_opened()
            logger.info(f"Marked recipient {recipient.id} as opened")
        
        logger.info(f"Message open recorded for message {message.id} (UUID: {uuid})")
        
    except Message.DoesNotExist:
        # Never leak existence, always return pixel
        logger.warning(f"Tracking pixel requested for non-existent UUID: {uuid}")
    
    # Always return the pixel
    return HttpResponse(PIXEL, content_type="image/png")


# -------------------- API/JSON Views --------------------
class ContactAutocompleteView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '')
        
        # FIXED: Include all subscribed contacts, not just active ones
        contacts = Contact.objects.filter(
            user=request.user,
            status='subscribed'
            # is_active=True  ← REMOVED THIS FILTER
        )
        
        if query:
            contacts = contacts.filter(
                Q(email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            )[:10]
        else:
            contacts = contacts[:10]
        
        results = []
        for contact in contacts:
            results.append({
                'id': contact.id,
                'email': contact.email,
                'name': contact.get_full_name(),
                'text': f"{contact.get_full_name()} <{contact.email}>",
                'is_active': contact.is_active
            })
        
        return JsonResponse({'results': results})


class ContactStatsView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        contacts = Contact.objects.filter(user=request.user)
        
        stats = {
            'total': contacts.count(),
            'subscribed': contacts.filter(status='subscribed').count(),
            'subscribed_active': contacts.filter(status='subscribed', is_active=True).count(),
            'subscribed_inactive': contacts.filter(status='subscribed', is_active=False).count(),
            'unsubscribed': contacts.filter(status='unsubscribed').count(),
            'bounced': contacts.filter(status='bounced').count(),
            'complaint': contacts.filter(status='complaint').count(),
            'pending': contacts.filter(status='pending').count(),
        }
        
        return JsonResponse(stats)