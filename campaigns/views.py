# campaigns/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from django.urls import reverse_lazy
from django.utils import timezone
from django.db import connection
from .models import Campaign
from .forms import CampaignForm


class CampaignListView(LoginRequiredMixin, ListView):
    """List all campaigns for the current user."""
    model = Campaign
    template_name = 'core/campaigns/campaign_list.html'
    context_object_name = 'campaigns'
    
    def get_queryset(self):
        return Campaign.objects.filter(user=self.request.user).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Campaign stats
        queryset = self.get_queryset()
        context.update({
            'total_campaigns': queryset.count(),
            'draft_campaigns': queryset.filter(status='draft').count(),
            'active_campaigns': queryset.filter(status='active').count(),
            'completed_campaigns': queryset.filter(status='completed').count(),
        })
        
        return context


class CampaignCreateView(LoginRequiredMixin, CreateView):
    """Create a new campaign."""
    model = Campaign
    form_class = CampaignForm
    template_name = 'core/campaigns/campaign_create.html'
    success_url = reverse_lazy('campaigns:list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        campaign = form.save(commit=False)
        
        # Check if campaign was set to "Send Now"
        schedule_type = form.cleaned_data.get('schedule_type', 'later')
        
        if schedule_type == 'now':
            # Only create, don't send yet
            messages.success(self.request, 'Campaign created! Use "Send Now" to start sending.')
        else:
            messages.success(self.request, 'Campaign created and scheduled successfully!')
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class CampaignUpdateView(LoginRequiredMixin, UpdateView):
    """Edit an existing campaign."""
    model = Campaign
    form_class = CampaignForm
    template_name = 'core/campaigns/campaign_edit.html'
    success_url = reverse_lazy('campaigns:list')
    
    def get_queryset(self):
        return Campaign.objects.filter(user=self.request.user)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Campaign updated successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class CampaignDetailView(LoginRequiredMixin, DetailView):
    """View campaign details and analytics."""
    model = Campaign
    template_name = 'core/campaigns/campaign_detail.html'
    context_object_name = 'campaign'
    
    def get_queryset(self):
        return Campaign.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaign = self.object
        
        # Add quick actions context
        context['can_send_now'] = campaign.can_be_sent()
        context['is_active'] = campaign.status == 'active'
        context['is_draft'] = campaign.status == 'draft'
        context['is_paused'] = campaign.status == 'paused'
        context['is_completed'] = campaign.status == 'completed'
        
        # Get message details
        message = campaign.messages.first()
        context['message'] = message
        
        if message:
            # Get recipient statistics
            recipients = message.recipients.all()
            context['recipient_count'] = recipients.count()
            context['sent_count'] = recipients.filter(status='sent').count()
            context['delivered_count'] = recipients.filter(status='delivered').count()
            context['failed_count'] = recipients.filter(status='failed').count()
            
            # Get open statistics
            from message_system.models import MessageOpen
            opens = MessageOpen.objects.filter(message=message)
            context['total_opens'] = opens.count()
            context['unique_opens'] = opens.values('ip_hash').distinct().count()
            
            # Calculate open rate
            if context['sent_count'] > 0:
                context['open_rate'] = round((context['unique_opens'] / context['sent_count']) * 100, 2)
            else:
                context['open_rate'] = 0
            
            # Get recent opens
            context['recent_opens'] = opens.select_related('recipient__contact').order_by('-opened_at')[:10]
        
        return context


class CampaignDeleteView(LoginRequiredMixin, View):
    """Delete a campaign."""
    
    def post(self, request, pk):
        campaign = get_object_or_404(Campaign, pk=pk, user=request.user)
        campaign_name = campaign.name
        
        try:
            # Method 1: Try Django ORM cascade delete
            campaign.delete()
            messages.success(request, f'Campaign "{campaign_name}" deleted successfully!')
            
        except Exception as e:
            # Method 2: Try to delete related objects manually
            try:
                # First delete all related messages and their recipients
                if hasattr(campaign, 'messages'):
                    # Get all message IDs
                    message_ids = list(campaign.messages.values_list('id', flat=True))
                    
                    if message_ids:
                        # Delete MessageRecipients first
                        from message_system.models import MessageRecipient
                        MessageRecipient.objects.filter(message_id__in=message_ids).delete()
                        
                        # Delete MessageOpens
                        from message_system.models import MessageOpen
                        MessageOpen.objects.filter(message_id__in=message_ids).delete()
                        
                        # Delete Messages
                        campaign.messages.all().delete()
                
                # Now delete the campaign
                campaign.delete()
                messages.success(request, f'Campaign "{campaign_name}" deleted successfully!')
                
            except Exception as e2:
                # Method 3: Use raw SQL as last resort
                try:
                    with connection.cursor() as cursor:
                        # Get message IDs
                        cursor.execute("SELECT id FROM message_system_message WHERE campaign_id = %s", [campaign.id])
                        message_ids = [row[0] for row in cursor.fetchall()]
                        
                        if message_ids:
                            # Delete MessageRecipients
                            placeholders = ','.join(['%s'] * len(message_ids))
                            cursor.execute(
                                f"DELETE FROM message_system_messagerecipient WHERE message_id IN ({placeholders})",
                                message_ids
                            )
                            
                            # Delete MessageOpens
                            cursor.execute(
                                f"DELETE FROM message_system_messageopen WHERE message_id IN ({placeholders})",
                                message_ids
                            )
                            
                            # Delete Messages
                            cursor.execute("DELETE FROM message_system_message WHERE campaign_id = %s", [campaign.id])
                        
                        # Finally delete the campaign
                        cursor.execute("DELETE FROM campaigns_campaign WHERE id = %s", [campaign.id])
                    
                    messages.success(request, f'Campaign "{campaign_name}" deleted successfully!')
                    
                except Exception as e3:
                    messages.error(request, f'Error deleting campaign: {str(e3)}')
                    return redirect('campaigns:detail', pk=campaign.pk)
        
        return redirect('campaigns:list')


class CampaignDuplicateView(LoginRequiredMixin, View):
    """Duplicate an existing campaign."""
    
    def post(self, request, pk):
        original = get_object_or_404(Campaign, pk=pk, user=request.user)
        
        # Get the original message
        original_message = original.messages.first()
        
        # Create a copy of the campaign
        campaign = Campaign.objects.create(
            user=request.user,
            name=f"{original.name} (Copy)",
            scheduled_at=original.scheduled_at,
            status='draft'
        )
        
        # Copy the message if it exists
        if original_message:
            campaign.create_message(
                subject=original_message.subject,
                body_plain=original_message.body_plain,
                body_html=original_message.body_html
            )
        
        messages.success(request, f'Campaign duplicated successfully!')
        return redirect('campaigns:edit', pk=campaign.pk)


class CampaignToggleStatusView(LoginRequiredMixin, View):
    """Toggle campaign status between draft/active/paused."""
    
    def post(self, request, pk):
        campaign = get_object_or_404(Campaign, pk=pk, user=request.user)
        
        current_status = campaign.status
        
        # Status transition logic
        if current_status == 'draft':
            # Check if campaign has required setup to be activated
            if not campaign.scheduled_at:
                messages.error(request, 'Campaign must be scheduled before activation.')
                return redirect('campaigns:detail', pk=campaign.pk)
            
            if not campaign.has_message_content():
                messages.error(request, 'Campaign must have email content before activation.')
                return redirect('campaigns:detail', pk=campaign.pk)
            
            if not campaign.has_recipients():
                messages.error(request, 'Campaign must have recipients before activation.')
                return redirect('campaigns:detail', pk=campaign.pk)
            
            campaign.status = 'active'
            action = 'activated'
            
        elif current_status == 'active':
            campaign.status = 'paused'
            action = 'paused'
            
        elif current_status == 'paused':
            campaign.status = 'active'
            action = 'resumed'
            
        elif current_status == 'completed':
            messages.error(request, 'Completed campaigns cannot be changed.')
            return redirect('campaigns:detail', pk=campaign.pk)
            
        else:
            messages.error(request, f'Cannot change status of {current_status} campaigns.')
            return redirect('campaigns:detail', pk=campaign.pk)
        
        campaign.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'Campaign {action} successfully!')
        
        # Check if we should redirect to list or detail
        redirect_to = request.POST.get('redirect_to', 'detail')
        if redirect_to == 'list':
            return redirect('campaigns:list')
        else:
            return redirect('campaigns:detail', pk=campaign.pk)


class CampaignSendNowView(LoginRequiredMixin, View):
    """Send campaign immediately (synchronous version)."""
    
    def post(self, request, pk):
        campaign = get_object_or_404(Campaign, pk=pk, user=request.user)
        
        # Check if campaign can be sent
        if not campaign.can_be_sent():
            if campaign.status == 'active':
                messages.warning(request, 'Campaign is already active and sending.')
            elif not campaign.has_message_content():
                messages.error(request, 'Campaign has no email content. Please edit the campaign first.')
            elif not campaign.has_recipients():
                messages.error(request, 'No recipients selected. Please edit the campaign to add recipients.')
            else:
                messages.error(request, 'Only draft or paused campaigns can be sent immediately.')
            return redirect('campaigns:detail', pk=campaign.pk)
        
        # Update scheduled time to now
        campaign.scheduled_at = timezone.now()
        
        # Change status to active
        campaign.status = 'active'
        campaign.save(update_fields=['scheduled_at', 'status', 'updated_at'])
        
        # Send emails synchronously (blocks until complete)
        try:
            from .tasks import send_campaign_emails
            sent_count, failed_count = send_campaign_emails(campaign.id)
            
            if sent_count > 0:
                messages.success(
                    request, 
                    f'Campaign sent! {sent_count} emails delivered successfully.'
                )
            if failed_count > 0:
                messages.warning(
                    request,
                    f'{failed_count} emails failed to send.'
                )
            if sent_count == 0 and failed_count > 0:
                messages.error(
                    request,
                    'All emails failed to send. Please check your SMTP configuration.'
                )
        except Exception as e:
            messages.error(request, f'Error sending campaign: {str(e)}')
        
        return redirect('campaigns:detail', pk=campaign.pk)


class CampaignPauseView(LoginRequiredMixin, View):
    """Pause an active campaign."""
    
    def post(self, request, pk):
        campaign = get_object_or_404(Campaign, pk=pk, user=request.user)
        
        if campaign.status != 'active':
            messages.error(request, 'Only active campaigns can be paused.')
            return redirect('campaigns:detail', pk=campaign.pk)
        
        campaign.status = 'paused'
        campaign.save(update_fields=['status', 'updated_at'])
        
        messages.success(request, 'Campaign paused successfully!')
        return redirect('campaigns:detail', pk=campaign.pk)


class CampaignResumeView(LoginRequiredMixin, View):
    """Resume a paused campaign."""
    
    def post(self, request, pk):
        campaign = get_object_or_404(Campaign, pk=pk, user=request.user)
        
        if campaign.status != 'paused':
            messages.error(request, 'Only paused campaigns can be resumed.')
            return redirect('campaigns:detail', pk=campaign.pk)
        
        campaign.status = 'active'
        campaign.save(update_fields=['status', 'updated_at'])
        
        messages.success(request, 'Campaign resumed successfully!')
        return redirect('campaigns:detail', pk=campaign.pk)