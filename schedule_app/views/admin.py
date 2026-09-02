from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import date
import json
from schedule_app.models import Role, Capability, Event, Shift, Ministry, VolunteerProfile

def check_admin_or_head(user):
    if not user.is_authenticated: return False
    if user.is_staff or user.is_superuser: return True
    return hasattr(user, 'volunteer_profile') and user.volunteer_profile.role and user.volunteer_profile.role.name == 'Department Head'

def admin_dashboard_view(request):
    """Renders the dashboard for staff/admin members."""
    if not check_admin_or_head(request.user):
        return redirect('login')

    total_volunteers   = VolunteerProfile.objects.count()
    total_departments  = Ministry.objects.count()
    upcoming_events    = Event.objects.filter(date__gte=date.today()).order_by('date')
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
    if not check_admin_or_head(request.user):
        return redirect('login')
    
    events = Event.objects.prefetch_related('offices').all()
    events_data = [{
        'id': e.id,
        'name': e.name,
        'title': f"{e.start_time.strftime('%I:%M %p')} - {e.name}",
        'date': e.date.isoformat(),
        'start_time': e.start_time.strftime('%I:%M %p'),
        'end_time': e.end_time.strftime('%I:%M %p'),
        'type': e.event_type,
        'description': e.description,
        'offices': [{'id': o.id, 'name': o.name} for o in e.offices.all()],
    } for e in events]
    
    return render(request, 'admin/admin-schedule.html', {
        'events_json': json.dumps(events_data)
    })

def admin_service_view(request):
    """Renders the Service management view and handles Event creation."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return redirect('login')
    
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        name = request.POST.get('name')
        event_type = request.POST.get('event_type')
        date_str = request.POST.get('date')
        start_time_str = request.POST.get('start_time')
        end_time_str = request.POST.get('end_time')
        description = request.POST.get('description', '')

        if name and event_type and date_str and start_time_str and end_time_str:
            if event_id:
                event = Event.objects.get(id=event_id)
                event.name = name
                event.event_type = event_type
                event.date = date_str
                event.start_time = start_time_str
                event.end_time = end_time_str
                event.description = description
                event.save()
            else:
                event = Event.objects.create(
                    name=name,
                    event_type=event_type,
                    date=date_str,
                    start_time=start_time_str,
                    end_time=end_time_str,
                    description=description
                )
            
            offices = request.POST.getlist('offices')
            event.offices.set(offices)
            
        return redirect('admin_service')
    
    base_query = Event.objects.filter(date__gte=date.today()).order_by('date').prefetch_related('shifts__ministry', 'shifts__volunteer', 'offices')
    ministries = Ministry.objects.all().order_by('name')
    
    return render(request, 'admin/admin-service.html', {
        'regular_events': base_query.filter(event_type='regular'),
        'scheduled_events': base_query.filter(event_type='scheduled'),
        'big_events': base_query.filter(event_type='big'),
        'ministries': ministries,
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
                        dept_head_role, created = Role.objects.get_or_create(
                            name="Department Head",
                            defaults={'badge': 'Head', 'theme': 'emerald', 'description': 'Head of a Ministry'}
                        )
                        if created:
                            # Auto-assign standard capabilities to the new role
                            default_caps = Capability.objects.filter(name__in=["Manage Departments", "Manage Volunteers", "Manage Schedule"])
                            dept_head_role.capabilities.set(default_caps)
                            
                        head_profile.role = dept_head_role
                        head_profile.save()
            else:
                ministry.head = None

        if ministry_id:
            # Edit existing
            ministry = Ministry.objects.filter(id=ministry_id).first()
            if ministry:
                old_head = ministry.head
                
                if name:
                    ministry.name = name
                ministry.description = description
                _assign_head(ministry, head_id)
                ministry.save()
                
                # If head was changed, check if old head needs downgrading
                if old_head and ministry.head != old_head:
                    # Remove the old head from the department entirely
                    ministry.volunteers.remove(old_head)
                    
                    if not Ministry.objects.filter(head=old_head).exists():
                        if not (old_head.user.is_superuser or old_head.user.is_staff):
                            volunteer_role, _ = Role.objects.get_or_create(
                                name="Volunteer",
                                defaults={'badge': 'Member', 'theme': 'blue', 'description': 'Regular Volunteer'}
                            )
                            old_head.role = volunteer_role
                            old_head.save()
                            
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

def admin_members_view(request):
    """Renders the global members list or a filtered list for Dept Heads."""
    if not check_admin_or_head(request.user):
        return redirect('login')
    
    is_staff = request.user.is_staff or request.user.is_superuser
    
    if is_staff:
        profiles = VolunteerProfile.objects.all().select_related('user', 'role').prefetch_related('ministries')
        all_ministries = Ministry.objects.all()
        return render(request, 'admin/admin-members.html', {'profiles': profiles, 'all_ministries': all_ministries})
    else:
        # Dept Head
        profile = request.user.volunteer_profile
        headed_ministries = profile.headed_ministries.all()
        # Only get volunteers who are part of the ministries this user heads
        profiles = VolunteerProfile.objects.filter(ministries__in=headed_ministries).distinct().select_related('user', 'role').prefetch_related('ministries')
        
        return render(request, 'dept-head/dept-head-members.html', {
            'profiles': profiles,
            'all_ministries': headed_ministries
        })

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
