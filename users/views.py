# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Q

from .forms import UserRegistrationForm, CustomAuthenticationForm, ProfileUpdateForm

# ==================== INDEX PAGE ====================

def index(request):
    """
    Index/Home page - shows landing page for Signalry.
    Shows different content based on authentication status.
    """
    return render(request, 'core/users/index.html')

# ==================== AUTHENTICATION ====================

def login_view(request):
    """
    User login view.
    Authenticates users and redirects to dashboard on success.
    """
    if request.user.is_authenticated:
        return redirect('users:dashboard')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Use display name instead of email
            welcome_name = user.get_display_name()
            messages.success(request, f'Welcome back, {welcome_name}!')
            
            return redirect('users:dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'core/users/login.html', {'form': form})

def register_view(request):
    """
    User registration view.
    Creates new user accounts with free plan.
    """
    if request.user.is_authenticated:
        return redirect('users:dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Log the user in after registration
            login(request, user)
            
            # Use display name instead of just generic message
            welcome_name = user.get_display_name()
            messages.success(request, f'Welcome to Signalry, {welcome_name}!')
            
            return redirect('users:dashboard')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'core/users/register.html', {'form': form})

def logout_view(request):
    """
    User logout view.
    Clears session and redirects to index page.
    """
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, 'You have been logged out.')
    
    return redirect('users:index')

# ==================== DASHBOARD ====================

class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view showing user overview and quick stats."""
    template_name = 'core/users/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # User info
        context['user'] = user
        
        # Calculate SMTP account statistics
        try:
            from smtp.models import SMTPAccount
            context['active_smtp_count'] = user.smtp_accounts.filter(status='active').count()
        except (ImportError, AttributeError):
            context['active_smtp_count'] = 0
        
        # Calculate campaign statistics
        try:
            from campaigns.models import Campaign
            campaigns = user.campaigns.all()
            context['active_campaigns_count'] = campaigns.filter(status='active').count()
            context['draft_campaigns_count'] = campaigns.filter(status='draft').count()
            context['paused_campaigns_count'] = campaigns.filter(status='paused').count()
            context['total_campaigns'] = campaigns.count()
        except (ImportError, AttributeError):
            context['active_campaigns_count'] = 0
            context['draft_campaigns_count'] = 0
            context['paused_campaigns_count'] = 0
            context['total_campaigns'] = 0
        
        # Try to get user analytics
        try:
            from analytics.models import UserAnalytics
            context['user_analytics'] = user.analytics
        except (ImportError, AttributeError):
            # Create a default analytics dictionary
            context['user_analytics'] = {
                'total_campaigns': context.get('total_campaigns', 0),
                'total_messages': 0,
                'active_smtp_accounts': context.get('active_smtp_count', 0),
            }
        
        # Try to get current plan
        try:
            from plans.models import Plan
            context['current_plan'] = user.current_plan
        except (ImportError, AttributeError):
            context['current_plan'] = None
        
        # Try to get recent campaigns
        try:
            context['recent_campaigns'] = user.campaigns.all().order_by('-created_at')[:3]
        except (AttributeError, ImportError):
            context['recent_campaigns'] = []
        
        # Try to get recent SMTP accounts
        try:
            context['recent_smtp_accounts'] = user.smtp_accounts.all().order_by('-created_at')[:3]
        except (AttributeError, ImportError):
            context['recent_smtp_accounts'] = []
        
        # Try to get recent alerts
        try:
            context['alerts'] = user.alerts.filter(is_resolved=False).order_by('-created_at')[:5]
        except (AttributeError, ImportError):
            context['alerts'] = []
        
        # Calculate total messages sent (check if Campaign has messages relationship)
        total_messages = 0
        try:
            from campaigns.models import Campaign
            # Check if Campaign model has a messages relationship
            campaigns_with_messages = Campaign.objects.filter(user=user)
            for campaign in campaigns_with_messages:
                # Try different possible field names for messages count
                if hasattr(campaign, 'messages'):
                    total_messages += campaign.messages.count()
                elif hasattr(campaign, 'email_messages'):
                    total_messages += campaign.email_messages.count()
                elif hasattr(campaign, 'sent_messages'):
                    total_messages += campaign.sent_messages.count()
        except (ImportError, AttributeError):
            pass
        
        # Update analytics with total messages
        if 'user_analytics' in context:
            if isinstance(context['user_analytics'], dict):
                context['user_analytics']['total_messages'] = total_messages
            elif hasattr(context['user_analytics'], 'total_messages'):
                context['user_analytics'].total_messages = total_messages
        
        return context

# ==================== PROFILE ====================

class ProfileEditView(LoginRequiredMixin, View):
    """User profile editing and management."""
    template_name = 'core/users/profile_edit.html'
    
    def get(self, request, *args, **kwargs):
        """Handle GET request - show profile form."""
        # Initialize form with current user data
        form = ProfileUpdateForm(instance=request.user)
        
        # Get context data
        context = self.get_context_data()
        context['form'] = form
        
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        """Handle POST request - update profile."""
        form = ProfileUpdateForm(request.POST, instance=request.user)
        
        if form.is_valid():
            user = form.save()
            
            # Show success message with updated name
            welcome_name = user.get_display_name()
            messages.success(request, f'Profile updated successfully! Welcome, {welcome_name}.')
            
            return redirect('users:profile_edit')
        else:
            # Form has errors, show error message
            messages.error(request, 'Please correct the errors below.')
        
        # Get context data with form errors
        context = self.get_context_data()
        context['form'] = form
        
        return render(request, self.template_name, context)
    
    def get_context_data(self, **kwargs):
        """Get common context data for both GET and POST."""
        user = self.request.user
        
        context = {
            'user': user,
        }
        
        # Try to get user analytics
        try:
            from analytics.models import UserAnalytics
            context['user_analytics'] = user.analytics
        except (ImportError, AttributeError):
            context['user_analytics'] = None
        
        # Try to get current plan
        try:
            from plans.models import Plan
            context['current_plan'] = user.current_plan
        except (ImportError, AttributeError):
            context['current_plan'] = None
        
        return context