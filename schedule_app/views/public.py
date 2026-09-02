from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from schedule_app.forms import LoginForm, RegisterForm

def login_view(request):
    """Handles user authentication and renders the login page."""
    form = LoginForm(request.POST or None)
    
    if request.method == 'POST' and form.is_valid():
        u = form.cleaned_data.get('username')
        p = form.cleaned_data.get('password')
        user = authenticate(request, username=u, password=p)
        
        if user is not None:
            auth_login(request, user)
            
            # Check for Department Head role
            is_dept_head = hasattr(user, 'volunteer_profile') and user.volunteer_profile.role and user.volunteer_profile.role.name == 'Department Head'
            
            # Redirect superusers and staff to admin dashboard
            if user.is_superuser or user.is_staff:
                return redirect('admin_dashboard')
                
            # Otherwise, regular user dashboard (including Dept Heads)
            return redirect('user_dashboard')
        else:
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
        
        messages.success(request, 'Account created successfully! Please sign in.')
        return redirect('login')
        
    return render(request, 'public/register.html', {'form': form})

def logout_view(request):
    """Handles user logout and clears any leftover session messages."""
    # Clear messages so they don't leak onto the login page
    storage = messages.get_messages(request)
    storage.used = True
    auth_logout(request)
    return redirect('landing_page')
