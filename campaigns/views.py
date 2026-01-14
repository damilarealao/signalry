# campaigns/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from django.urls import reverse_lazy
from django.db.models import Q
from django.utils import timezone
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
        
        # Check plan limits
        user = self.request.user
        try:
            from plans.models import Plan
            user_plan = getattr(user, "current_plan", None)
            plan_type = getattr(user_plan, "plan_type", "free") if user_plan else "free"
            plan_limit = Plan.objects.get_limits(plan_type)["active_campaigns"]
            context['campaign_limit'] = plan_limit
        except:
            context['campaign_limit'] = None
        
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
        messages.success(self.request, 'Campaign created successfully!')
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


class CampaignDeleteView(LoginRequiredMixin, View):
    """Delete a campaign."""
    
    def post(self, request, pk):
        campaign = get_object_or_404(Campaign, pk=pk, user=request.user)
        campaign_name = campaign.name
        campaign.delete()
        messages.success(request, f'Campaign "{campaign_name}" deleted successfully!')
        return redirect('campaigns:list')


class CampaignDuplicateView(LoginRequiredMixin, View):
    """Duplicate an existing campaign."""
    
    def post(self, request, pk):
        original = get_object_or_404(Campaign, pk=pk, user=request.user)
        
        # Create a copy
        campaign = Campaign.objects.create(
            user=request.user,
            name=f"{original.name} (Copy)",
            scheduled_at=original.scheduled_at,
            status='draft'
        )
        
        messages.success(request, f'Campaign duplicated successfully!')
        return redirect('campaigns:edit', pk=campaign.pk)


class CampaignToggleStatusView(LoginRequiredMixin, View):
    """Toggle campaign status between draft/active/paused."""
    
    def post(self, request, pk):
        campaign = get_object_or_404(Campaign, pk=pk, user=request.user)
        
        current_status = campaign.status
        if current_status == 'draft':
            campaign.status = 'active'
            action = 'activated'
        elif current_status == 'active':
            campaign.status = 'paused'
            action = 'paused'
        elif current_status == 'paused':
            campaign.status = 'active'
            action = 'resumed'
        else:
            messages.error(request, f'Cannot change status of {current_status} campaigns.')
            return redirect('campaigns:list')
        
        campaign.save()
        messages.success(request, f'Campaign {action} successfully!')
        return redirect('campaigns:list')