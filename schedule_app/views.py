from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db.models import Q
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from datetime import date
from .forms import LoginForm, RegisterForm, UserProfileForm
from .models import Role, Capability, Event, Shift, Ministry, VolunteerProfile

# --- PUBLIC VIEWS ---
def login_view(request):
    """Handles user authentication and renders the login page."""
    form = LoginForm(request.POST or None)
    
    if request.method == 'POST' and form.is_valid():
        u = form.cleaned_data.get('username')
        p = form.cleaned_data.get('password')
        user = authenticate(request, username=u, password=p)
        
        if user is not None:
            auth_login(request, user)
            # Redirect superusers to admin dashboard, else user dashboard
            if user.is_superuser or user.is_staff:
                return redirect('admin_dashboard')
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

# --- USER VIEWS ---

@login_required
def user_profile_view(request):
    """Renders the detailed user profile page (Tailwind Admin style)."""
    form = UserProfileForm(request.POST or None, user=request.user)
    
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('user_profile')
        
    context = {
        'form': form,
    }
    return render(request, 'shared/my-profile.html', context)


def user_dashboard_view(request):
    """Renders the main dashboard for authenticated users."""
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'user/user-dashboard.html')

# --- ADMIN VIEWS ---
def admin_dashboard_view(request):
    """Renders the dashboard for staff/admin members."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return redirect('login')

    from datetime import date as _date
    total_volunteers   = VolunteerProfile.objects.count()
    total_departments  = Ministry.objects.count()
    upcoming_events    = Event.objects.filter(date__gte=_date.today()).order_by('date')
    open_shifts        = Shift.objects.filter(volunteer__isnull=True).count()
    next_event         = upcoming_events.first()
    next_event_open_shifts = Shift.objects.filter(event=next_event, volunteer__isnull=True).count() if next_event else 0

    return render(request, 'admin/admin-dashboard.html', {
        'total_volunteers':       total_volunteers,
        'total_departments':      total_departments,
        'upcoming_count':         upcoming_events.count(),
        'open_shifts':            open_shifts,
        'next_event':             next_event,
        'next_event_open_shifts': next_event_open_shifts,
        'recent_events':          upcoming_events[:5],
    })

def admin_schedule_view(request):
    """Renders the calendar schedule view for admins."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return redirect('login')
    
    events = Event.objects.all()
    events_data = [{
        'id': e.id,
        'title': f"{e.start_time.strftime('%I:%M %p')} - {e.name}",
        'date': e.date.isoformat(),
    } for e in events]
    
    return render(request, 'admin/admin-schedule.html', {
        'events_json': json.dumps(events_data)
    })

def admin_service_view(request):
    """Renders the Service management view and handles Event creation."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return redirect('login')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        event_type = request.POST.get('event_type')
        date_str = request.POST.get('date')
        start_time_str = request.POST.get('start_time')
        end_time_str = request.POST.get('end_time')
        description = request.POST.get('description', '')

        if name and event_type and date_str and start_time_str and end_time_str:
            Event.objects.create(
                name=name,
                event_type=event_type,
                date=date_str,
                start_time=start_time_str,
                end_time=end_time_str,
                description=description
            )
        return redirect('admin_service')
    
    base_query = Event.objects.filter(date__gte=date.today()).order_by('date').prefetch_related('shifts__ministry', 'shifts__volunteer')
    
    return render(request, 'admin/admin-service.html', {
        'regular_events': base_query.filter(event_type='regular'),
        'scheduled_events': base_query.filter(event_type='scheduled'),
        'big_events': base_query.filter(event_type='big'),
    })

def admin_departments_view(request):
    """Renders the main departments page and handles department creation/editing."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return redirect('login')
    
    if request.method == 'POST':
        ministry_id = request.POST.get('ministry_id')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        head_id = request.POST.get('head_id')

        def _assign_head(ministry, head_id):
            """Helper: assign head, upgrade role, and auto-add to department members."""
            if head_id:
                head_profile = VolunteerProfile.objects.filter(id=head_id).first()
                if head_profile:
                    ministry.head = head_profile
                    # Auto-add as a member of the department
                    ministry.volunteers.add(head_profile)
                    # Upgrade role to Department Head if not already staff/superuser
                    if not (head_profile.user.is_superuser or head_profile.user.is_staff):
                        dept_head_role, _ = Role.objects.get_or_create(
                            name="Department Head",
                            defaults={'badge': 'Head', 'theme': 'emerald', 'description': 'Head of a Ministry'}
                        )
                        head_profile.role = dept_head_role
                        head_profile.save()
            else:
                ministry.head = None

        if ministry_id:
            # Edit existing
            ministry = Ministry.objects.filter(id=ministry_id).first()
            if ministry:
                if name:
                    ministry.name = name
                ministry.description = description
                _assign_head(ministry, head_id)
                ministry.save()
                messages.success(request, f'Department "{ministry.name}" updated successfully!')
        else:
            # Create new
            if name:
                ministry = Ministry.objects.create(name=name, description=description)
                _assign_head(ministry, head_id)
                ministry.save()
                messages.success(request, f'Department "{name}" created successfully!')
                
        return redirect('admin_departments')
        
    ministries = Ministry.objects.prefetch_related('volunteers', 'head__user').all()
    all_volunteers = VolunteerProfile.objects.select_related('user').all()
    
    return render(request, 'admin/admin-departments.html', {
        'ministries': ministries,
        'all_volunteers': all_volunteers
    })

# JSON endpoint for Alpine.js volunteer autocomplete
def search_volunteers(request):
    """Return JSON list of volunteers matching the query for Alpine.js autocomplete."""
    from django.http import JsonResponse as _JsonResponse
    q = request.GET.get('q', '').strip()
    volunteers = VolunteerProfile.objects.select_related('user')
    if q:
        volunteers = volunteers.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__username__icontains=q)
        )[:15]
    results = [
        {'id': vol.id, 'label': f"{vol.user.get_full_name()} ({vol.user.username})"}
        for vol in volunteers
    ]
    return _JsonResponse({'results': results})

def admin_members_view(request):
    """Renders the global members list."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return redirect('login')
    
    profiles = VolunteerProfile.objects.all().select_related('user', 'role').prefetch_related('ministries')
    all_ministries = Ministry.objects.all()
        
    return render(request, 'admin/admin-members.html', {'profiles': profiles, 'all_ministries': all_ministries})

def admin_user_roles_view(request):
    """Renders the User Roles and Permissions management view."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return redirect('login')
    
    roles = Role.objects.prefetch_related('capabilities', 'volunteers__user').all()
    all_capabilities = Capability.objects.all()
    
    return render(request, 'admin/admin-user-roles.html', {
        'roles': roles,
        'all_capabilities': all_capabilities
    })

def api_update_role(request):
    """API Endpoint to update a role via POST request."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            role_id = data.get('role_id')
            name = data.get('name')
            description = data.get('description')
            capabilities = data.get('capabilities', [])
            
            role = Role.objects.get(id=role_id)
            if name:
                role.name = name
            if description is not None:
                role.description = description
                
            role.capabilities.set(capabilities)
            role.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid method'}, status=405)
    
def api_update_ministries(request):
    """API Endpoint to update a user's ministries via POST request."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            profile_id = data.get('profile_id')
            ministry_ids = data.get('ministry_ids', [])
            
            profile = VolunteerProfile.objects.get(id=profile_id)
            profile.ministries.set(ministry_ids)
            profile.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

def api_assign_role(request):
    """API Endpoint to assign a user to a role via POST request."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            role_id = data.get('role_id')
            user_id = data.get('user_id')
            
            role = Role.objects.get(id=role_id)
            profile = VolunteerProfile.objects.get(id=user_id)
            profile.role = role
            profile.save()
            
            return JsonResponse({
                'success': True,
                'user': {
                    'id': profile.id,
                    'name': profile.user.get_full_name() or profile.user.username,
                    'email': profile.user.email
                }
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
            
    return JsonResponse({'error': 'Invalid method'}, status=405)

def api_remove_role(request):
    """API Endpoint to remove a user from a role via POST request."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            
            profile = VolunteerProfile.objects.get(id=user_id)
            profile.role = None
            profile.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
            
    return JsonResponse({'error': 'Invalid method'}, status=405)
