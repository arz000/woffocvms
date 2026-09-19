from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse_lazy
from schedule_app.forms import LoginForm, RegisterForm, DirectPasswordResetForm, PasswordResetRequestForm, CustomSetPasswordForm
from schedule_app.utils import log_activity



def login_view(request):
    """Handles user authentication and renders the login page."""
    form = LoginForm(request.POST or None)
    
    if request.method == 'POST' and form.is_valid():
        u = form.cleaned_data.get('username')
        p = form.cleaned_data.get('password')
        user = authenticate(request, username=u, password=p)
        
        if user is not None:
            auth_login(request, user)
            log_activity(
                request=request,
                action_type='AUTH',
                category='Auth',
                description=f"User '{user.username}' logged in successfully."
            )
            
            # Check for Department Head role
            is_dept_head = hasattr(user, 'volunteer_profile') and user.volunteer_profile.role and user.volunteer_profile.role.name == 'Department Head'
            
            # Redirect superusers and staff to admin dashboard
            if user.is_superuser or user.is_staff:
                return redirect('admin_dashboard')
                
            # Otherwise, regular user dashboard (including Dept Heads)
            return redirect('user_dashboard')
        else:
            log_activity(
                request=request,
                action_type='SECURITY',
                category='Auth',
                description=f"Failed login attempt for username '{u}'."
            )
            messages.error(request, 'Invalid username or password.')
            
    return render(request, 'public/login.html', {'form': form})

def register_view(request):
    """Handles user registration and renders the registration page."""
    form = RegisterForm(request.POST or None)
    
    if request.method == 'POST' and form.is_valid():
        # Create the user using the form data
        user = User.objects.create_user(
            username=form.cleaned_data.get('username'),
            email=form.cleaned_data.get('email'),
            password=form.cleaned_data.get('password'),
            first_name=form.cleaned_data.get('first_name'),
            last_name=form.cleaned_data.get('last_name')
        )
        
        log_activity(
            request=request,
            user=user,
            action_type='CREATE',
            category='Auth',
            description=f"New user registered: '{user.username}' ({user.email})."
        )
        
        messages.success(request, 'Account created successfully! Please sign in.')
        return redirect('login')
        
    return render(request, 'public/register.html', {'form': form})

def logout_view(request):
    """Handles user logout and clears any leftover session messages."""
    if request.user.is_authenticated:
        log_activity(
            request=request,
            action_type='AUTH',
            category='Auth',
            description=f"User '{request.user.username}' logged out."
        )
    # Clear messages so they don't leak onto the login page
    storage = messages.get_messages(request)
    storage.used = True
    auth_logout(request)
    return redirect('landing_page')


def password_reset_view(request):
    """Direct password reset without requiring email verification."""
    form = DirectPasswordResetForm(request.POST or None)
    
    if request.method == 'POST' and form.is_valid():
        user = form.cleaned_data.get('user')
        new_password = form.cleaned_data.get('new_password')
        
        user.set_password(new_password)
        user.save()
        
        log_activity(
            request=request,
            user=user,
            action_type='SECURITY',
            category='Auth',
            description=f"Password was reset directly for user '{user.username}'."
        )
        
        messages.success(request, 'Password reset successfully! Please sign in with your new password.')
        return redirect('login')
        
    return render(request, 'public/password_reset.html', {'form': form})



class CustomPasswordResetView(auth_views.PasswordResetView):
    template_name = 'public/password_reset.html'
    form_class = PasswordResetRequestForm
    email_template_name = 'public/password_reset_email.html'
    subject_template_name = 'public/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')

    def form_valid(self, form):
        email = form.cleaned_data.get('email')
        log_activity(
            request=self.request,
            action_type='SECURITY',
            category='Auth',
            description=f"Password reset requested for email '{email}'."
        )
        return super().form_valid(form)


class CustomPasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'public/password_reset_done.html'


class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'public/password_reset_confirm.html'
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy('password_reset_complete')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.user
        if user:
            log_activity(
                request=self.request,
                user=user,
                action_type='SECURITY',
                category='Auth',
                description=f"Password successfully reset for user '{user.username}'."
            )
        return response


class CustomPasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = 'public/password_reset_complete.html'

