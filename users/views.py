# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin

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
        
        # Try to get user analytics
        try:
            from analytics.models import UserAnalytics
            context['user_analytics'] = user.analytics
        except:
            context['user_analytics'] = None
        
        # Try to get current plan
        try:
            from plans.models import Plan
            context['current_plan'] = user.current_plan
        except:
            context['current_plan'] = None
        
        # Try to get recent campaigns
        try:
            context['campaigns'] = user.campaigns.all()[:5]
        except:
            context['campaigns'] = []
        
        # Try to get recent alerts
        try:
            context['alerts'] = user.alerts.filter(is_resolved=False)[:5]
        except:
            context['alerts'] = []
        
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
        except:
            context['user_analytics'] = None
        
        # Try to get current plan
        try:
            from plans.models import Plan
            context['current_plan'] = user.current_plan
        except:
            context['current_plan'] = None
        
        return context