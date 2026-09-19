from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import date
from django.utils import timezone
import json
from schedule_app.models import Role, Capability, Event, Shift, Ministry, VolunteerProfile, ActivityLog
from schedule_app.utils import log_activity

def check_admin_or_head(user):
    if not user.is_authenticated: return False
    if user.is_staff or user.is_superuser: return True
    return hasattr(user, 'volunteer_profile') and user.volunteer_profile.role and user.volunteer_profile.role.name == 'Department Head'

def admin_dashboard_view(request):
    """Renders the dashboard for staff/admin members with stats and department distribution."""
    if not check_admin_or_head(request.user):
        return redirect('login')

    total_volunteers   = VolunteerProfile.objects.count()
    total_departments  = Ministry.objects.count()
    upcoming_events    = Event.objects.filter(date__gte=date.today()).order_by('date')
    open_shifts        = Shift.objects.filter(volunteer__isnull=True).count()
    next_event         = upcoming_events.first()
    next_event_open_shifts = Shift.objects.filter(event=next_event, volunteer__isnull=True).count() if next_event else 0

    # Department Volunteer Distribution for Donut Chart & Visual Bars
    import math
    ministries = Ministry.objects.prefetch_related('volunteers').all()
    dept_distribution = []
    total_dept_members = 0

    for m in ministries:
        v_count = m.volunteers.count()
        total_dept_members += v_count
        dept_distribution.append({
            'name': m.name,
            'count': v_count,
        })
    
    # Sort descending so the largest department appears first
    dept_distribution.sort(key=lambda x: x['count'], reverse=True)

    # Distinct vibrant colors for high visual contrast
    palette = [
        '#10b981', # Emerald
        '#3b82f6', # Blue
        '#8b5cf6', # Purple
        '#f59e0b', # Amber
        '#ec4899', # Pink
        '#06b6d4', # Cyan
        '#f97316', # Orange
        '#6366f1', # Indigo
        '#14b8a6', # Teal
        '#64748b', # Slate
    ]

    circumference = 2 * math.pi * 58 # ~364.42
    current_offset = 0

    for idx, d in enumerate(dept_distribution):
        d['color'] = palette[idx % len(palette)]
        fraction = (d['count'] / total_dept_members) if total_dept_members > 0 else 0
        d['percentage'] = round(fraction * 100)
        length = fraction * circumference
        d['dasharray'] = f"{length:.2f} {circumference - length:.2f}"
        d['dashoffset'] = f"{-current_offset:.2f}"
        current_offset += length

    return render(request, 'admin/admin-dashboard.html', {
        'total_volunteers':       total_volunteers,
        'total_departments':      total_departments,
        'total_dept_members':     total_dept_members,
        'upcoming_count':         upcoming_events.count(),
        'open_shifts':            open_shifts,
        'next_event':             next_event,
        'next_event_open_shifts': next_event_open_shifts,
        'recent_events':          upcoming_events[:5],
        'dept_distribution':      dept_distribution,
    })

def admin_schedule_view(request):
    """Renders the calendar schedule view for admins and department heads."""
    if not check_admin_or_head(request.user):
        return redirect('login')
    
    events = Event.objects.all().prefetch_related('offices', 'shifts__volunteer', 'shifts__ministry', 'shifts__job').order_by('date', 'start_time')
    events_data = []
    for e in events:
        all_shifts = list(e.shifts.all())
        total_shifts = len(all_shifts)
        filled_shifts = [s for s in all_shifts if s.volunteer_id is not None]
        unfilled_shifts = [s for s in all_shifts if s.volunteer_id is None]
        
        needed_roles_count = {}
        for s in unfilled_shifts:
            r_name = s.job.title if s.job else (s.ministry.name if s.ministry else "Volunteer")
            needed_roles_count[r_name] = needed_roles_count.get(r_name, 0) + 1

        needed_roles = [{'role': r, 'count': c} for r, c in needed_roles_count.items()]

        team = []
        for s in filled_shifts:
            if s.volunteer:
                team.append({
                    'name': s.volunteer.get_full_name() or s.volunteer.username,
                    'role': s.job.title if s.job else (s.ministry.name if s.ministry else "Volunteer"),
                    'ministry': s.ministry.name if s.ministry else "",
                })

        events_data.append({
            'id': e.id,
            'name': e.name,
            'title': f"{e.start_time.strftime('%I:%M %p')} - {e.name}",
            'date': e.date.isoformat(),
            'formatted_date': e.date.strftime('%A, %B %d, %Y'),
            'start_time': e.start_time.strftime('%I:%M %p'),
            'end_time': e.end_time.strftime('%I:%M %p'),
            'time_range': f"{e.start_time.strftime('%I:%M %p')} - {e.end_time.strftime('%I:%M %p')}",
            'type': e.event_type,
            'description': e.description,
            'total_shifts': total_shifts,
            'filled_count': len(filled_shifts),
            'needed_count': len(unfilled_shifts),
            'needed_roles': needed_roles,
            'team': team,
            'offices': [{'id': o.id, 'name': o.name} for o in e.offices.all()],
        })
    
    return render(request, 'admin/admin-schedule.html', {
        'events_json': json.dumps(events_data),
        'today': date.today().isoformat(),
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
            try:
                from datetime import datetime as dt
                event_date = dt.strptime(date_str, '%Y-%m-%d').date()
                if event_date < date.today():
                    messages.error(request, 'Cannot schedule or create events on past dates.')
                    return redirect('admin_service')
            except ValueError:
                pass

            if event_id:
                event = Event.objects.get(id=event_id)
                event.name = name
                event.event_type = event_type
                event.date = date_str
                event.start_time = start_time_str
                event.end_time = end_time_str
                event.description = description
                event.save()
                log_activity(
                    request=request,
                    action_type='UPDATE',
                    category='Events',
                    description=f"Updated event '{name}' scheduled on {date_str}."
                )
                messages.success(request, f'Event "{name}" updated successfully.')
            else:
                event = Event.objects.create(
                    name=name,
                    event_type=event_type,
                    date=date_str,
                    start_time=start_time_str,
                    end_time=end_time_str,
                    description=description
                )
                log_activity(
                    request=request,
                    action_type='CREATE',
                    category='Events',
                    description=f"Created new event '{name}' for {date_str}."
                )
                messages.success(request, f'Event "{name}" created successfully.')
            
            offices = request.POST.getlist('offices')
            event.offices.set(offices)
            
        return redirect('admin_service')
    
    base_query = Event.objects.prefetch_related('shifts__ministry', 'shifts__volunteer', 'offices')
    today_val = date.today()
    upcoming_events = base_query.filter(date__gte=today_val).order_by('date', 'start_time')
    past_events = base_query.filter(date__lt=today_val).order_by('-date', '-start_time')
    ministries = Ministry.objects.all().order_by('name')
    
    return render(request, 'admin/admin-service.html', {
        'regular_events': upcoming_events.filter(event_type='regular'),
        'scheduled_events': upcoming_events.filter(event_type='scheduled'),
        'big_events': upcoming_events.filter(event_type='big'),
        'past_regular_events': past_events.filter(event_type='regular'),
        'past_scheduled_events': past_events.filter(event_type='scheduled'),
        'past_big_events': past_events.filter(event_type='big'),
        'total_upcoming': upcoming_events.count(),
        'total_past': past_events.count(),
        'ministries': ministries,
        'today': today_val.isoformat(),
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
                            
                log_activity(
                    request=request,
                    action_type='UPDATE',
                    category='Departments',
                    description=f"Updated department '{ministry.name}' details and leadership."
                )
                messages.success(request, f'Department "{ministry.name}" updated successfully!')
        else:
            # Create new
            if name:
                ministry = Ministry.objects.create(name=name, description=description)
                _assign_head(ministry, head_id)
                ministry.save()
                log_activity(
                    request=request,
                    action_type='CREATE',
                    category='Departments',
                    description=f"Created new department '{name}'."
                )
                messages.success(request, f'Department "{name}" created successfully!')
                
        return redirect('admin_departments')
        
    ministries = Ministry.objects.prefetch_related('volunteers', 'head__user').all()
    all_volunteers = VolunteerProfile.objects.select_related('user').all()
    
    return render(request, 'admin/admin-departments.html', {
        'ministries': ministries,
        'all_volunteers': all_volunteers
    })

def admin_members_view(request):
    """Renders the members list for Admins, Dept Heads, or Volunteers in their respective departments."""
    if not request.user.is_authenticated:
        return redirect('login')
    
    is_staff = request.user.is_staff or request.user.is_superuser
    profile = getattr(request.user, 'volunteer_profile', None)
    
    if is_staff:
        base_profiles = VolunteerProfile.objects.all().select_related('user', 'role').prefetch_related('ministries').order_by('user__first_name', 'user__last_name', 'user__username')
        all_ministries = Ministry.objects.all().order_by('name')
        
        total_members = base_profiles.count()
        assigned_count = base_profiles.filter(ministries__isnull=False).distinct().count()
        unassigned_count = base_profiles.filter(ministries__isnull=True).count()
        
        profiles_data = []
        for p in base_profiles:
            fn = p.user.first_name.strip() if p.user.first_name else ""
            ln = p.user.last_name.strip() if p.user.last_name else ""
            full_name = f"{fn} {ln}".strip() if (fn or ln) else p.user.username
            first_letter = (fn[0] if fn else (p.user.username[0] if p.user.username else "U")).upper()
            
            profiles_data.append({
                'id': p.id,
                'user_id': p.user.id,
                'username': p.user.username,
                'full_name': full_name,
                'first_letter': first_letter,
                'role': p.role.name if p.role else "Volunteer",
                'email': p.user.email or "—",
                'phone': p.phone_number or "—",
                'gender': p.gender or "—",
                'birthday': p.birthday.strftime('%b %d, %Y') if p.birthday else "—",
                'ministries': [{'id': m.id, 'name': m.name} for m in p.ministries.all()],
                'ministry_ids': [m.id for m in p.ministries.all()],
            })
        
        ministries_data = [{'id': m.id, 'name': m.name} for m in all_ministries]
        return render(request, 'admin/admin-members.html', {
            'profiles_data': profiles_data,
            'ministries_data': ministries_data,
            'all_ministries': all_ministries,
            'total_members': total_members,
            'assigned_count': assigned_count,
            'unassigned_count': unassigned_count,
        })
    elif profile and profile.headed_ministries.exists():
        headed_ministries = profile.headed_ministries.all()
        base_profiles = VolunteerProfile.objects.filter(ministries__in=headed_ministries).distinct().select_related('user', 'role').prefetch_related('ministries').order_by('user__first_name', 'user__last_name', 'user__username')
        
        total_members = base_profiles.count()
        assigned_count = total_members
        unassigned_count = VolunteerProfile.objects.filter(ministries__isnull=True).count()
        
        profiles_data = []
        for p in base_profiles:
            fn = p.user.first_name.strip() if p.user.first_name else ""
            ln = p.user.last_name.strip() if p.user.last_name else ""
            full_name = f"{fn} {ln}".strip() if (fn or ln) else p.user.username
            first_letter = (fn[0] if fn else (p.user.username[0] if p.user.username else "U")).upper()
            
            profiles_data.append({
                'id': p.id,
                'user_id': p.user.id,
                'username': p.user.username,
                'full_name': full_name,
                'first_letter': first_letter,
                'role': p.role.name if p.role else "Volunteer",
                'email': p.user.email or "—",
                'phone': p.phone_number or "—",
                'gender': p.gender or "—",
                'birthday': p.birthday.strftime('%b %d, %Y') if p.birthday else "—",
                'ministries': [{'id': m.id, 'name': m.name} for m in p.ministries.all()],
                'ministry_ids': [m.id for m in p.ministries.all()],
            })
            
        ministries_data = [{'id': m.id, 'name': m.name} for m in headed_ministries]
        return render(request, 'dept-head/dept-head-members.html', {
            'profiles_data': profiles_data,
            'ministries_data': ministries_data,
            'all_ministries': headed_ministries,
            'total_members': total_members,
            'assigned_count': assigned_count,
            'unassigned_count': unassigned_count,
        })
    else:
        my_ministries = profile.ministries.all() if profile else Ministry.objects.none()
        if my_ministries.exists():
            base_profiles = VolunteerProfile.objects.filter(ministries__in=my_ministries).distinct().select_related('user', 'role').prefetch_related('ministries').order_by('user__first_name', 'user__last_name', 'user__username')
        else:
            base_profiles = VolunteerProfile.objects.filter(id=profile.id) if profile else VolunteerProfile.objects.none()
            
        total_members = base_profiles.count()
        
        profiles_data = []
        for p in base_profiles:
            fn = p.user.first_name.strip() if p.user.first_name else ""
            ln = p.user.last_name.strip() if p.user.last_name else ""
            full_name = f"{fn} {ln}".strip() if (fn or ln) else p.user.username
            first_letter = (fn[0] if fn else (p.user.username[0] if p.user.username else "U")).upper()
            
            profiles_data.append({
                'id': p.id,
                'user_id': p.user.id,
                'username': p.user.username,
                'full_name': full_name,
                'first_letter': first_letter,
                'role': p.role.name if p.role else "Volunteer Member",
                'email': p.user.email or "—",
                'phone': p.phone_number or "—",
                'gender': p.gender or "—",
                'birthday': p.birthday.strftime('%b %d, %Y') if p.birthday else "—",
                'ministries': [{'id': m.id, 'name': m.name} for m in p.ministries.all()],
                'ministry_ids': [m.id for m in p.ministries.all()],
            })
            
        return render(request, 'volunteer/volunteer-members.html', {
            'profiles_data': profiles_data,
            'my_ministries': my_ministries,
            'total_members': total_members,
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

def admin_activity_log_view(request):
    """Renders the System Activity Log with real-time filtering, search, and pagination."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return redirect('login')
    
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    action_type = request.GET.get('action', '').strip()
    date_filter = request.GET.get('date', '').strip()
    
    logs = ActivityLog.objects.select_related('user').all()
    
    # Text Search Filter
    if query:
        logs = logs.filter(
            Q(description__icontains=query) |
            Q(actor_name__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(ip_address__icontains=query)
        )
    
    # Category Filter
    if category and category != 'All':
        logs = logs.filter(category=category)
        
    # Action Type Filter
    if action_type and action_type != 'All':
        logs = logs.filter(action_type=action_type)
        
    # Date Filter
    today = timezone.now().date()
    if date_filter == 'today':
        logs = logs.filter(created_at__date=today)
    elif date_filter == 'week':
        week_ago = today - timezone.timedelta(days=7)
        logs = logs.filter(created_at__date__gte=week_ago)
    elif date_filter == 'month':
        month_ago = today - timezone.timedelta(days=30)
        logs = logs.filter(created_at__date__gte=month_ago)

    # Compute high-level stats
    total_activities = ActivityLog.objects.count()
    today_activities = ActivityLog.objects.filter(created_at__date=today).count()
    security_activities = ActivityLog.objects.filter(Q(action_type='SECURITY') | Q(category='Auth')).count()
    unique_actors = ActivityLog.objects.exclude(actor_name='System').values('actor_name').distinct().count()

    # Pagination
    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Available Categories & Action Types for filtering
    categories = [
        ('All', 'All Categories'),
        ('Roles', 'Roles & Permissions'),
        ('Members', 'Members'),
        ('Departments', 'Departments'),
        ('Events', 'Events'),
        ('Shifts', 'Shifts'),
        ('Jobs', 'Department Jobs'),
        ('Auth', 'Authentication & Access'),
        ('General', 'General'),
    ]

    action_types = [
        ('All', 'All Actions'),
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'),
        ('DELETE', 'Deleted'),
        ('ASSIGN', 'Assigned'),
        ('AUTH', 'Authentication'),
        ('SECURITY', 'Security'),
    ]

    return render(request, 'admin/admin-activity-log.html', {
        'page_obj': page_obj,
        'logs': page_obj.object_list,
        'total_activities': total_activities,
        'today_activities': today_activities,
        'security_activities': security_activities,
        'unique_actors': unique_actors,
        'categories': categories,
        'action_types': action_types,
        'selected_category': category or 'All',
        'selected_action': action_type or 'All',
        'selected_date': date_filter or 'all',
        'query': query,
    })
