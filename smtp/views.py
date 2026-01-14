# smtp/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, View
from django.urls import reverse_lazy
from django.db.models import Q
from .models import SMTPAccount
from .forms import SMTPAccountForm


class SMTPListView(LoginRequiredMixin, ListView):
    """List all SMTP accounts for the current user."""
    model = SMTPAccount
    template_name = 'core/smtp/smtp_list.html'
    context_object_name = 'smtp_accounts'
    
    def get_queryset(self):
        return SMTPAccount.objects.filter(user=self.request.user).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_count'] = self.get_queryset().filter(status='active').count()
        context['total_count'] = self.get_queryset().count()
        return context


class SMTPCreateView(LoginRequiredMixin, CreateView):
    """Create a new SMTP account."""
    model = SMTPAccount
    form_class = SMTPAccountForm
    template_name = 'core/smtp/smtp_add.html'
    success_url = reverse_lazy('smtp:list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'SMTP account created successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class SMTPUpdateView(LoginRequiredMixin, UpdateView):
    """Edit an existing SMTP account."""
    model = SMTPAccount
    form_class = SMTPAccountForm
    template_name = 'core/smtp/smtp_edit.html'
    success_url = reverse_lazy('smtp:list')
    
    def get_queryset(self):
        return SMTPAccount.objects.filter(user=self.request.user)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'SMTP account updated successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class SMTPDeleteView(LoginRequiredMixin, View):
    """Delete an SMTP account."""
    
    def post(self, request, pk):
        smtp_account = get_object_or_404(SMTPAccount, pk=pk, user=request.user)
        smtp_account.delete()
        messages.success(request, 'SMTP account deleted successfully!')
        return redirect('smtp:list')


class SMTPTestView(LoginRequiredMixin, View):
    """Test SMTP account connection."""
    
    def post(self, request, pk):
        smtp_account = get_object_or_404(SMTPAccount, pk=pk, user=request.user)
        
        try:
            # Use the manager's validation method
            SMTPAccount.objects.validate_smtp(
                smtp_account.smtp_host,
                smtp_account.smtp_port,
                smtp_account.smtp_user,
                smtp_account.get_password()
            )
            smtp_account.reset_failures()
            messages.success(request, 'SMTP connection test successful!')
        except Exception as e:
            smtp_account.mark_failure()
            messages.error(request, f'SMTP test failed: {str(e)}')
        
        return redirect('smtp:list')


class SMTPToggleStatusView(LoginRequiredMixin, View):
    """Toggle SMTP account status between active/inactive."""
    
    def post(self, request, pk):
        smtp_account = get_object_or_404(SMTPAccount, pk=pk, user=request.user)
        
        if smtp_account.status == 'active':
            smtp_account.status = 'disabled'
            action = 'disabled'
        else:
            smtp_account.status = 'active'
            smtp_account.reset_failures()
            action = 'activated'
        
        smtp_account.save()
        messages.success(request, f'SMTP account {action} successfully!')
        return redirect('smtp:list')