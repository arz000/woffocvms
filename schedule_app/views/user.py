from schedule_app.models import Event
from django.utils import timezone
from django.db.models import Count
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from schedule_app.forms import UserProfileForm

@login_required
def user_profile_view(request):
    """Renders the enhanced user profile page."""
    from schedule_app.models import Shift
    from django.contrib.auth import update_session_auth_hash
    
    form = UserProfileForm(request.POST or None, user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action', 'update_profile')
        from schedule_app.utils import log_activity
        
        if action == 'change_password':
            current_pwd = request.POST.get('current_password', '')
            new_pwd = request.POST.get('new_password', '')
            confirm_pwd = request.POST.get('confirm_password', '')
            
            if not request.user.check_password(current_pwd):
                messages.error(request, 'Current password is incorrect.')
            elif len(new_pwd) < 6:
                messages.error(request, 'New password must be at least 6 characters long.')
            elif new_pwd != confirm_pwd:
                messages.error(request, 'New passwords do not match.')
            else:
                request.user.set_password(new_pwd)
                request.user.save()
                update_session_auth_hash(request, request.user)
                log_activity(
                    request=request,
                    action_type='SECURITY',
                    category='Auth',
                    description=f"User '{request.user.username}' changed their account password."
                )
                messages.success(request, 'Password changed successfully.')
                return redirect('user_profile')
        else:
            if form.is_valid():
                form.save()
                log_activity(
                    request=request,
                    action_type='UPDATE',
                    category='Members',
                    description=f"Member '{request.user.get_full_name() or request.user.username}' updated profile information."
                )
                messages.success(request, 'Profile updated successfully.')
                return redirect('user_profile')
        
    total_shifts_served = Shift.objects.filter(volunteer=request.user).count()
    upcoming_shifts_count = Shift.objects.filter(volunteer=request.user, event__date__gte=timezone.now().date()).count()
    profile = getattr(request.user, 'volunteer_profile', None)
    my_ministries = profile.ministries.all() if profile else []

    context = {
        'form': form,
        'profile': profile,
        'my_ministries': my_ministries,
        'total_shifts_served': total_shifts_served,
        'upcoming_shifts_count': upcoming_shifts_count,
    }
    return render(request, 'shared/my-profile.html', context)

def user_dashboard_view(request):
    """Renders the main dashboard for authenticated users."""
    if not request.user.is_authenticated:
        return redirect('login')
    
    context = {}
    if hasattr(request.user, 'volunteer_profile'):
        profile = request.user.volunteer_profile
        is_dept_head = profile.role and profile.role.name == 'Department Head'
        context['is_dept_head'] = is_dept_head
        today = timezone.now().date()
        
        if is_dept_head:
            headed_ministries = profile.headed_ministries.prefetch_related('volunteers__user', 'volunteers__role').all()
            
            # Get all member profiles across headed ministries
            from schedule_app.models import VolunteerProfile
            dept_members = VolunteerProfile.objects.filter(
                ministries__in=headed_ministries
            ).distinct().select_related('user', 'role')
            
            # Get upcoming events for their departments
            upcoming_events = Event.objects.filter(
                offices__in=headed_ministries,
                date__gte=today
            ).distinct().order_by('date', 'start_time')[:5]
            
            context['headed_ministries'] = headed_ministries
            context['total_members'] = dept_members.count()
            context['dept_members'] = dept_members[:5]
            context['upcoming_events'] = upcoming_events
            context['total_departments'] = headed_ministries.count()
            
            return render(request, 'dept-head/dept-head-dashboard.html', context)
        else:
            # Regular Volunteer Dashboard
            from schedule_app.models import Shift
            my_ministries = profile.ministries.all().prefetch_related('head__user', 'volunteers')
            
            # Assigned upcoming shifts
            my_shifts = Shift.objects.filter(
                volunteer=request.user,
                event__date__gte=today
            ).select_related('event', 'ministry', 'job').order_by('event__date', 'event__start_time')
            
            # Open opportunities (unassigned shifts in user's departments or all)
            if my_ministries.exists():
                open_shifts = Shift.objects.filter(
                    volunteer__isnull=True,
                    ministry__in=my_ministries,
                    event__date__gte=today
                ).select_related('event', 'ministry', 'job').order_by('event__date', 'event__start_time')
            else:
                open_shifts = Shift.objects.filter(
                    volunteer__isnull=True,
                    event__date__gte=today
                ).select_related('event', 'ministry', 'job').order_by('event__date', 'event__start_time')

                
            # Past shifts count
            completed_shifts_count = Shift.objects.filter(
                volunteer=request.user,
                event__date__lt=today
            ).count()

            all_upcoming_events = Event.objects.filter(date__gte=today).order_by('date', 'start_time')
            from schedule_app.models import Ministry
            all_ministries = Ministry.objects.all().order_by('name')

            context.update({
                'profile': profile,
                'my_ministries': my_ministries,
                'all_ministries': all_ministries,
                'all_upcoming_events': all_upcoming_events,
                'upcoming_events': all_upcoming_events,
                'my_shifts': my_shifts,
                'open_shifts': open_shifts[:4],
                'total_upcoming_shifts': my_shifts.count(),
                'total_open_shifts': open_shifts.count(),
                'completed_shifts_count': completed_shifts_count,
            })
            
    return render(request, 'volunteer/volunteer-dashboard.html', context)

@login_required
def volunteer_create_shift_view(request):
    """Allows volunteers to self-schedule or create a serving shift."""
    from schedule_app.models import Event, Ministry, Shift
    
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        ministry_id = request.POST.get('ministry_id')
        start_time = request.POST.get('start_time') or None
        end_time = request.POST.get('end_time') or None
        
        event = Event.objects.filter(id=event_id).first()
        ministry = Ministry.objects.filter(id=ministry_id).first()
        
        if event and ministry:
            # Check if an existing open shift exists for this event & ministry
            open_shift = Shift.objects.filter(event=event, ministry=ministry, volunteer__isnull=True).first()
            if open_shift:
                open_shift.volunteer = request.user
                if start_time: open_shift.start_time = start_time
                if end_time: open_shift.end_time = end_time
                open_shift.save()
            else:
                # Create a new shift record directly assigned to volunteer
                Shift.objects.create(
                    event=event,
                    ministry=ministry,
                    volunteer=request.user,
                    start_time=start_time,
                    end_time=end_time
                )
            messages.success(request, f"You have successfully scheduled your shift for {event.name} ({ministry.name})!")
        else:
            messages.error(request, "Please select a valid event and department.")
            
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'user_dashboard'
    return redirect(next_url)

@login_required
def volunteer_calendar_view(request):
    """Renders the full visual Calendar of upcoming church services & events for volunteers."""
    import json
    from schedule_app.models import Shift, Event, Unavailability
    
    today = timezone.now().date()
    events = Event.objects.all().prefetch_related('offices', 'shifts__volunteer', 'shifts__ministry', 'shifts__job').order_by('date', 'start_time')
    
    events_data = []
    for e in events:
        my_shift = e.shifts.filter(volunteer=request.user).first()
        is_assigned = my_shift is not None
        my_role = ""
        my_ministry = ""
        if my_shift:
            my_role = my_shift.job.title if my_shift.job else (my_shift.ministry.name if my_shift.ministry else "Volunteer")
            my_ministry = my_shift.ministry.name if my_shift.ministry else ""

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
            'is_assigned': is_assigned,
            'my_role': my_role,
            'my_ministry': my_ministry,
            'total_shifts': total_shifts,
            'filled_count': len(filled_shifts),
            'needed_count': len(unfilled_shifts),
            'needed_roles': needed_roles,
            'team': team,
            'offices': [{'id': o.id, 'name': o.name} for o in e.offices.all()],
        })
    
    return render(request, 'volunteer/volunteer-calendar.html', {
        'events_json': json.dumps(events_data),
        'today': today.isoformat(),
    })

@login_required
def volunteer_schedule_view(request):
    """Dedicated 'Schedule' tab where volunteers manage the dates they cannot serve (unavailable / blackout dates) & view commitments."""
    from schedule_app.models import Shift, Event, Unavailability
    import datetime
    
    today = timezone.now().date()
    
    # Handle adding / removing unavailable dates
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_unavailability':
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date') or None
            reason = request.POST.get('reason', '').strip()
            other_reason = request.POST.get('other_reason', '').strip()
            
            final_reason = other_reason if (reason == 'Other' and other_reason) else (reason or 'Unavailable')
            
            if start_date:
                try:
                    s_date = datetime.date.fromisoformat(start_date)
                    if s_date < today:
                        messages.error(request, "Cannot set unavailable dates in the past.")
                        return redirect('volunteer_schedule')
                except ValueError:
                    pass

                Unavailability.objects.create(
                    volunteer=request.user,
                    start_date=start_date,
                    end_date=end_date,
                    reason=final_reason,
                    status='pending'
                )
                messages.success(request, "Your unavailable date request has been submitted for department head confirmation.")
            return redirect('volunteer_schedule')
            
        elif action == 'delete_unavailability':
            unavail_id = request.POST.get('unavailability_id')
            Unavailability.objects.filter(id=unavail_id, volunteer=request.user).delete()
            messages.info(request, "Unavailable date request removed.")
            return redirect('volunteer_schedule')

    # Volunteer's active upcoming unavailable dates
    unavailabilities = Unavailability.objects.filter(
        volunteer=request.user,
        start_date__gte=today
    ).order_by('start_date')
    
    # Active scheduled shifts (Upcoming) — grouped by event
    raw_shifts = Shift.objects.filter(
        volunteer=request.user,
        event__date__gte=today
    ).select_related('event', 'ministry', 'job').order_by('event__date', 'event__start_time')

    # Group shifts by event so multiple roles in the same event appear as one card
    from collections import OrderedDict
    grouped_shifts = OrderedDict()
    for shift in raw_shifts:
        eid = shift.event_id
        if eid not in grouped_shifts:
            grouped_shifts[eid] = {
                'event': shift.event,
                'shifts': [],
            }
        grouped_shifts[eid]['shifts'].append(shift)
    my_shifts_grouped = list(grouped_shifts.values())

    # Past served shifts (History) — also grouped by event
    raw_past_shifts = Shift.objects.filter(
        volunteer=request.user,
        event__date__lt=today
    ).select_related('event', 'ministry', 'job').order_by('-event__date', '-event__start_time')

    grouped_past = OrderedDict()
    for shift in raw_past_shifts:
        eid = shift.event_id
        if eid not in grouped_past:
            grouped_past[eid] = {
                'event': shift.event,
                'shifts': [],
            }
        grouped_past[eid]['shifts'].append(shift)
    past_shifts_grouped = list(grouped_past.values())

    return render(request, 'volunteer/volunteer-schedule.html', {
        'unavailabilities': unavailabilities,
        'my_shifts': my_shifts_grouped,
        'past_shifts': past_shifts_grouped,
        'today': today.isoformat(),
    })


@login_required
def volunteer_opportunities_view(request):
    """Allows volunteers to browse open shifts and sign up / claim a slot."""
    from schedule_app.models import Shift
    
    today = timezone.now().date()
    profile = getattr(request.user, 'volunteer_profile', None)
    my_ministries = profile.ministries.all() if profile else []
    
    # Handle Signup / Leave POST action
    if request.method == 'POST':
        shift_id = request.POST.get('shift_id')
        action = request.POST.get('action', 'signup')
        
        shift = Shift.objects.filter(id=shift_id).select_related('event').first()
        if shift and shift.event.date >= today:
            if action == 'signup' and shift.volunteer is None:
                shift.volunteer = request.user
                shift.save()
                messages.success(request, f"You successfully signed up for {shift.event.name} ({shift.job.title if shift.job else shift.ministry.name})!")
            elif action == 'cancel' and shift.volunteer == request.user:
                shift.volunteer = None
                shift.save()
                messages.success(request, f"You have successfully removed yourself from {shift.event.name}.")
                
        return redirect('volunteer_opportunities')
        
    # Open Shifts for signup
    if my_ministries.exists():
        dept_open_shifts = Shift.objects.filter(
            volunteer__isnull=True,
            ministry__in=my_ministries,
            event__date__gte=today
        ).select_related('event', 'ministry').order_by('event__date', 'event__start_time')
    else:
        dept_open_shifts = Shift.objects.none()
        
    all_open_shifts = Shift.objects.filter(
        volunteer__isnull=True,
        event__date__gte=today
    ).select_related('event', 'ministry').order_by('event__date', 'event__start_time')
    
    my_claimed_shifts = Shift.objects.filter(
        volunteer=request.user,
        event__date__gte=today
    ).select_related('event', 'ministry').order_by('event__date', 'event__start_time')
    
    return render(request, 'volunteer/volunteer-opportunities.html', {
        'dept_open_shifts': dept_open_shifts,
        'all_open_shifts': all_open_shifts,
        'my_claimed_shifts': my_claimed_shifts,
        'my_ministries': my_ministries,
    })


@login_required
def volunteer_join_department_view(request):
    """Allows volunteers to browse all departments and join or leave them."""
    from schedule_app.models import Ministry, VolunteerProfile, DepartmentLeaveRequest, DepartmentJoinRequest
    from schedule_app.utils import log_activity
    
    profile = getattr(request.user, 'volunteer_profile', None)
    if not profile:
        profile, _ = VolunteerProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        ministry_id = request.POST.get('ministry_id')
        ministry = Ministry.objects.filter(id=ministry_id).first()
        
        if ministry:
            if action == 'join':
                if ministry in profile.ministries.all():
                    messages.info(request, f"You are already a member of {ministry.name}.")
                else:
                    # Check if already has a pending join request
                    existing_request = DepartmentJoinRequest.objects.filter(
                        volunteer=request.user,
                        ministry=ministry,
                        status='pending'
                    ).first()

                    if existing_request:
                        messages.info(request, f"You already have a pending join request for {ministry.name}.")
                    else:
                        reason = request.POST.get('reason', '').strip()
                        DepartmentJoinRequest.objects.create(
                            volunteer=request.user,
                            ministry=ministry,
                            reason=reason,
                            status='pending'
                        )
                        log_activity(
                            request=request,
                            action_type='UPDATE',
                            category='Volunteer',
                            description=f"Submitted request to join department '{ministry.name}'"
                        )
                        messages.success(request, f"Your request to join {ministry.name} has been submitted for review.")
            elif action == 'leave':
                if ministry in profile.ministries.all():
                    # Check if already has a pending leave request
                    existing_request = DepartmentLeaveRequest.objects.filter(
                        volunteer=request.user,
                        ministry=ministry,
                        status='pending'
                    ).first()

                    if existing_request:
                        messages.info(request, f"You already have a pending leave request for {ministry.name}.")
                    else:
                        reason = request.POST.get('reason', '').strip()
                        DepartmentLeaveRequest.objects.create(
                            volunteer=request.user,
                            ministry=ministry,
                            reason=reason,
                            status='pending'
                        )
                        log_activity(
                            request=request,
                            action_type='UPDATE',
                            category='Volunteer',
                            description=f"Submitted request to leave department '{ministry.name}'"
                        )
                        messages.success(request, f"Your request to leave the {ministry.name} department has been submitted for review.")
                else:
                    messages.info(request, f"You are not currently a member of {ministry.name}.")
        else:
            messages.error(request, "Department not found.")
            
        return redirect('volunteer_join_department')

    # GET: fetch all departments
    all_ministries = Ministry.objects.prefetch_related('volunteers', 'head__user', 'jobs').order_by('name')
    my_ministry_ids = set(profile.ministries.values_list('id', flat=True))

    # Get ministries with pending leave requests by this volunteer
    pending_leave_ministry_ids = set(DepartmentLeaveRequest.objects.filter(
        volunteer=request.user,
        status='pending'
    ).values_list('ministry_id', flat=True))

    # Get ministries with pending join requests by this volunteer
    pending_join_ministry_ids = set(DepartmentJoinRequest.objects.filter(
        volunteer=request.user,
        status='pending'
    ).values_list('ministry_id', flat=True))

    ministries_data = []
    for m in all_ministries:
        is_member = m.id in my_ministry_ids
        has_pending_leave = m.id in pending_leave_ministry_ids
        has_pending_join = m.id in pending_join_ministry_ids
        ministries_data.append({
            'id': m.id,
            'name': m.name,
            'description': m.description,
            'is_member': is_member,
            'has_pending_leave': has_pending_leave,
            'has_pending_join': has_pending_join,
            'volunteers_count': m.volunteers.count(),
            'jobs_count': m.jobs.count(),
            'head_name': m.head.user.get_full_name() if (m.head and m.head.user) else None,
        })

    my_count = len(my_ministry_ids)
    available_count = max(0, len(all_ministries) - my_count)

    return render(request, 'volunteer/volunteer-join-department.html', {
        'ministries_data': ministries_data,
        'total_departments': len(all_ministries),
        'my_departments_count': my_count,
        'available_departments_count': available_count,
    })


@login_required
def dept_head_events_view(request):
    """Lists events assigned to the dept head's departments."""
    from schedule_app.models import Event, Ministry
    from django.utils import timezone
    
    profile = request.user.volunteer_profile
    headed_ministries = profile.headed_ministries.all()
    
    if not headed_ministries.exists():
        return redirect('user_dashboard')
    
    today = timezone.now().date()
    
    # Annotate each event with filled_count
    def annotate_events(events):
        for event in events:
            event.filled_count = event.shifts.filter(volunteer__isnull=False).count()
        return events
    
    upcoming_query = Event.objects.filter(
        offices__in=headed_ministries,
        date__gte=today
    ).distinct().order_by('date', 'start_time').prefetch_related('offices', 'shifts__volunteer', 'shifts__ministry')

    past_query = Event.objects.filter(
        offices__in=headed_ministries,
        date__lt=today
    ).distinct().order_by('-date', '-start_time').prefetch_related('offices', 'shifts__volunteer', 'shifts__ministry')
    
    regular_events = annotate_events(list(upcoming_query.filter(event_type='regular')))
    scheduled_events = annotate_events(list(upcoming_query.filter(event_type='scheduled')))
    big_events = annotate_events(list(upcoming_query.filter(event_type='big')))

    past_regular_events = annotate_events(list(past_query.filter(event_type='regular')))
    past_scheduled_events = annotate_events(list(past_query.filter(event_type='scheduled')))
    past_big_events = annotate_events(list(past_query.filter(event_type='big')))
    
    return render(request, 'dept-head/dept-head-events.html', {
        'regular_events': regular_events,
        'scheduled_events': scheduled_events,
        'big_events': big_events,
        'past_regular_events': past_regular_events,
        'past_scheduled_events': past_scheduled_events,
        'past_big_events': past_big_events,
        'total_upcoming': upcoming_query.count(),
        'total_past': past_query.count(),
    })

@login_required
def dept_head_event_detail_view(request, event_id):
    """Shows created department jobs & shifts for a specific event and allows assigning multiple available volunteers."""
    from schedule_app.models import Event, Shift, VolunteerProfile, DepartmentJob, Unavailability
    from django.contrib.auth.models import User
    
    profile = request.user.volunteer_profile
    headed_ministries = profile.headed_ministries.all()
    
    event = Event.objects.prefetch_related('offices', 'shifts__volunteer', 'shifts__ministry', 'shifts__job').get(id=event_id)
    
    # Handle POST to update volunteer assignments for a job
    if request.method == 'POST':
        if event.date < timezone.now().date():
            messages.error(request, "Cannot modify assignments for events that have already passed.")
            return redirect('dept_head_event_detail', event_id=event_id)

        job_id = request.POST.get('job_id')
        action = request.POST.get('action', 'save_assignments')
        
        if job_id:
            job = DepartmentJob.objects.filter(id=job_id, ministry__in=headed_ministries).first()
            if job:
                if action == 'save_assignments':
                    selected_vol_ids = request.POST.getlist('volunteer_ids')
                    
                    # Convert to integers
                    valid_vol_ids = []
                    for vid in selected_vol_ids:
                        try:
                            valid_vol_ids.append(int(vid))
                        except (ValueError, TypeError):
                            pass
                    
                    # Check which volunteers are actually available on event.date
                    from django.db.models import Q
                    unavail_ids = set(Unavailability.objects.filter(
                        Q(start_date=event.date) | Q(start_date__lte=event.date, end_date__gte=event.date),
                        volunteer_id__in=valid_vol_ids
                    ).values_list('volunteer_id', flat=True))
                    
                    # Remove unassigned shifts for this job
                    Shift.objects.filter(
                        event=event,
                        job=job,
                        ministry=job.ministry
                    ).exclude(volunteer_id__in=valid_vol_ids).delete()
                    
                    # Create shifts for newly selected available volunteers
                    assigned_count = 0
                    for vid in valid_vol_ids:
                        if vid not in unavail_ids:
                            Shift.objects.get_or_create(
                                event=event,
                                ministry=job.ministry,
                                job=job,
                                volunteer_id=vid,
                            )
                            assigned_count += 1
                    
                    if unavail_ids:
                        messages.warning(request, f'Assignments saved, but {len(unavail_ids)} volunteer(s) could not be assigned due to schedule conflicts.')
                    else:
                        messages.success(request, f'Updated assignments for {job.title} successfully ({assigned_count} volunteer{"s" if assigned_count != 1 else ""} assigned).')
                
                elif action == 'clear_job':
                    Shift.objects.filter(event=event, job=job, ministry=job.ministry).delete()
                    messages.success(request, f'Cleared all assignments for {job.title}.')
        
        return redirect('dept_head_event_detail', event_id=event_id)

    # 1. Fetch unavailabilities on event.date (handles both single-day and date ranges)
    from django.db.models import Q
    unavail_list = Unavailability.objects.filter(
        Q(start_date=event.date) | Q(start_date__lte=event.date, end_date__gte=event.date)
    ).values('volunteer_id', 'reason')
    unavail_map = {u['volunteer_id']: u['reason'] or 'Unavailable' for u in unavail_list}

    # 2. Get all department jobs for headed ministries
    dept_jobs = DepartmentJob.objects.filter(
        ministry__in=headed_ministries
    ).select_related('ministry', 'team_leader__user').prefetch_related('assigned_volunteers__user')

    # 3. All existing shifts for this event and headed ministries
    existing_shifts = list(event.shifts.filter(ministry__in=headed_ministries).select_related('ministry', 'volunteer', 'job'))
    
    # Map job_id -> list of shifts
    shifts_by_job = {}
    for s in existing_shifts:
        if s.job_id:
            if s.job_id not in shifts_by_job:
                shifts_by_job[s.job_id] = []
            shifts_by_job[s.job_id].append(s)

    # 4. Department members across headed ministries
    dept_members = list(VolunteerProfile.objects.filter(
        ministries__in=headed_ministries
    ).distinct().select_related('user', 'role'))

    # Build Ministry data structure
    ministries_data = []
    for ministry in headed_ministries:
        m_jobs = [j for j in dept_jobs if j.ministry_id == ministry.id]
        m_members = [m for m in dept_members if ministry in m.ministries.all()]
        
        # If no specific members in this ministry, fallback to all headed department members
        if not m_members:
            m_members = dept_members

        # Prepare member list with availability for this ministry
        members_with_avail = []
        for m in m_members:
            user_id = m.user.id
            is_unavail = user_id in unavail_map
            members_with_avail.append({
                'id': user_id,
                'name': m.user.get_full_name() or m.user.username,
                'is_available': not is_unavail,
                'unavail_reason': unavail_map.get(user_id, ''),
                'role_name': m.role.name if m.role else 'Volunteer',
            })

        # Build job item data
        job_rows = []
        for job in m_jobs:
            j_shifts = shifts_by_job.get(job.id, [])
            assigned_vols = [s.volunteer for s in j_shifts if s.volunteer]
            assigned_user_ids = {v.id for v in assigned_vols}
            
            # Job candidates: ONLY volunteers who are assigned to this specific role or is team leader
            job_vol_ids = set(job.assigned_volunteers.values_list('user_id', flat=True))
            if job.team_leader:
                job_vol_ids.add(job.team_leader.user_id)
            
            candidates = []
            for mem in members_with_avail:
                if mem['id'] in job_vol_ids:
                    is_leader = (job.team_leader and job.team_leader.user_id == mem['id'])
                    is_assigned = mem['id'] in assigned_user_ids
                    candidates.append({
                        **mem,
                        'is_preferred': True,
                        'is_leader': is_leader,
                        'is_assigned': is_assigned,
                    })
            
            # Sort: assigned first, then available first, then leader first, then name
            candidates.sort(key=lambda x: (not x['is_assigned'], not x['is_available'], not x['is_leader'], x['name'].lower()))

            job_rows.append({
                'job': job,
                'assigned_volunteers': assigned_vols,
                'assigned_user_ids': assigned_user_ids,
                'candidates': candidates,
                'available_count': sum(1 for c in candidates if c['is_available']),
            })

        ministries_data.append({
            'ministry': ministry,
            'job_rows': job_rows,
            'total_jobs': len(job_rows),
            'filled_roles_count': sum(1 for j in job_rows if len(j['assigned_volunteers']) > 0),
            'total_assigned_count': sum(len(j['assigned_volunteers']) for j in job_rows),
            'members': members_with_avail,
        })

    return render(request, 'dept-head/dept-head-event-detail.html', {
        'event': event,
        'ministries_data': ministries_data,
        'is_past_event': event.date < timezone.now().date(),
        'today': timezone.now().date().isoformat(),
    })

@login_required
def dept_head_availability_view(request):
    """Allows Department Heads to view and approve/decline unavailable/blackout date requests ONLY for volunteers in their headed departments."""
    from schedule_app.models import Unavailability, VolunteerProfile, Ministry, Shift
    from schedule_app.utils import log_activity
    from django.db.models import Q
    
    today = timezone.now().date()
    profile = getattr(request.user, 'volunteer_profile', None)
    is_admin = request.user.is_staff or request.user.is_superuser
    
    if profile and profile.headed_ministries.exists():
        # ONLY ministries headed by this Dept Head
        headed_ministries = profile.headed_ministries.all()
    elif is_admin:
        headed_ministries = Ministry.objects.all()
    else:
        messages.error(request, "Access restricted to Department Heads.")
        return redirect('user_dashboard')
        
    # Get ONLY members who belong to ministries headed by this Dept Head
    dept_members = VolunteerProfile.objects.filter(
        ministries__in=headed_ministries
    ).distinct().select_related('user', 'role').prefetch_related('ministries')
    
    member_user_ids = [m.user_id for m in dept_members]

    # Handle POST actions (Approve / Decline)
    if request.method == 'POST':
        action = request.POST.get('action')
        unavail_id = request.POST.get('unavailability_id')
        unavail = Unavailability.objects.filter(
            id=unavail_id,
            volunteer_id__in=member_user_ids
        ).first()

        if unavail:
            v_name = unavail.volunteer.get_full_name() or unavail.volunteer.username
            date_range_str = f"{unavail.start_date.strftime('%b %d, %Y')}"
            if unavail.end_date and unavail.end_date != unavail.start_date:
                date_range_str += f" - {unavail.end_date.strftime('%b %d, %Y')}"

            if action == 'approve':
                unavail.status = 'approved'
                unavail.reviewed_at = timezone.now()
                unavail.reviewed_by = request.user
                unavail.save()

                # Release any upcoming shifts for this volunteer during this blackout window across headed ministries
                end_dt = unavail.end_date or unavail.start_date
                conflicting_shifts = Shift.objects.filter(
                    volunteer=unavail.volunteer,
                    ministry__in=headed_ministries,
                    event__date__gte=unavail.start_date,
                    event__date__lte=end_dt
                )
                shifts_cleared = conflicting_shifts.count()
                conflicting_shifts.update(volunteer=None)

                log_activity(
                    request=request,
                    action_type='UPDATE',
                    category='Schedule',
                    description=f"Approved unavailable dates for '{v_name}' ({date_range_str}) with {shifts_cleared} shift(s) released"
                )
                messages.success(request, f"Unavailable date request confirmed for {v_name}. Any overlapping shifts were released.")

            elif action == 'decline':
                unavail.status = 'declined'
                unavail.reviewed_at = timezone.now()
                unavail.reviewed_by = request.user
                unavail.save()

                log_activity(
                    request=request,
                    action_type='UPDATE',
                    category='Schedule',
                    description=f"Declined unavailable dates request for '{v_name}' ({date_range_str})"
                )
                messages.info(request, f"Unavailable date request declined for {v_name}.")
        else:
            messages.error(request, "Unavailable date request not found or access denied.")

        return redirect('dept_head_availability')

    # GET: List unavailabilities
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all').strip()

    unavail_qs = Unavailability.objects.filter(
        volunteer_id__in=member_user_ids,
        start_date__gte=today
    ).select_related('volunteer', 'volunteer__volunteer_profile', 'reviewed_by').order_by('start_date')

    if q:
        unavail_qs = unavail_qs.filter(
            Q(volunteer__first_name__icontains=q) |
            Q(volunteer__last_name__icontains=q) |
            Q(volunteer__username__icontains=q) |
            Q(reason__icontains=q)
        )

    all_list = list(unavail_qs)
    pending_count = sum(1 for u in all_list if getattr(u, 'status', 'pending') == 'pending')
    approved_count = sum(1 for u in all_list if getattr(u, 'status', 'pending') == 'approved')
    declined_count = sum(1 for u in all_list if getattr(u, 'status', 'pending') == 'declined')

    if status_filter in ['pending', 'approved', 'declined']:
        unavail_qs = unavail_qs.filter(status=status_filter)

    return render(request, 'dept-head/dept-head-availability.html', {
        'headed_ministries': headed_ministries,
        'unavailabilities': unavail_qs,
        'total_unavailabilities': len(all_list),
        'pending_count': pending_count,
        'approved_count': approved_count,
        'declined_count': declined_count,
        'total_members': dept_members.count(),
        'search_query': q,
        'status_filter': status_filter,
    })

@login_required
def dept_head_leave_requests_view(request):
    """Allows Department Heads to view and approve or decline volunteer requests to leave their departments."""
    from schedule_app.models import DepartmentLeaveRequest, VolunteerProfile, Ministry, Shift
    from schedule_app.utils import log_activity
    from django.db.models import Q
    
    profile = getattr(request.user, 'volunteer_profile', None)
    is_admin = request.user.is_staff or request.user.is_superuser
    
    if profile and profile.headed_ministries.exists():
        headed_ministries = profile.headed_ministries.all()
    elif is_admin:
        headed_ministries = Ministry.objects.all()
    else:
        messages.error(request, "Access restricted to Department Heads.")
        return redirect('user_dashboard')

    # Handle POST actions (Approve / Decline)
    if request.method == 'POST':
        action = request.POST.get('action')
        request_id = request.POST.get('request_id')
        leave_req = DepartmentLeaveRequest.objects.filter(
            id=request_id,
            ministry__in=headed_ministries
        ).first()

        if leave_req:
            volunteer_profile = getattr(leave_req.volunteer, 'volunteer_profile', None)
            v_name = leave_req.volunteer.get_full_name() or leave_req.volunteer.username
            m_name = leave_req.ministry.name

            if action == 'approve':
                leave_req.status = 'approved'
                leave_req.reviewed_at = timezone.now()
                leave_req.reviewed_by = request.user
                leave_req.save()

                if volunteer_profile and leave_req.ministry in volunteer_profile.ministries.all():
                    volunteer_profile.ministries.remove(leave_req.ministry)

                # Remove any upcoming shifts for this volunteer in this ministry
                today = timezone.now().date()
                upcoming_shifts = Shift.objects.filter(
                    volunteer=leave_req.volunteer,
                    ministry=leave_req.ministry,
                    event__date__gte=today
                )
                shifts_cleared = upcoming_shifts.count()
                upcoming_shifts.update(volunteer=None)

                log_activity(
                    request=request,
                    action_type='UPDATE',
                    category='Departments',
                    description=f"Approved leave request for '{v_name}' from department '{m_name}' ({shifts_cleared} upcoming shifts released)"
                )
                messages.success(request, f"Leave request approved for {v_name}. Member has been removed from {m_name}.")

            elif action == 'decline':
                leave_req.status = 'declined'
                leave_req.reviewed_at = timezone.now()
                leave_req.reviewed_by = request.user
                leave_req.save()

                log_activity(
                    request=request,
                    action_type='UPDATE',
                    category='Departments',
                    description=f"Declined leave request for '{v_name}' from department '{m_name}'"
                )
                messages.info(request, f"Leave request declined for {v_name}.")
        else:
            messages.error(request, "Leave request not found or access denied.")

        return redirect('dept_head_leave_requests')

    # GET: List requests
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all').strip()

    requests_qs = DepartmentLeaveRequest.objects.filter(
        ministry__in=headed_ministries
    ).select_related('volunteer', 'volunteer__volunteer_profile', 'ministry', 'reviewed_by').order_by('-created_at')

    if q:
        requests_qs = requests_qs.filter(
            Q(volunteer__first_name__icontains=q) |
            Q(volunteer__last_name__icontains=q) |
            Q(volunteer__username__icontains=q) |
            Q(ministry__name__icontains=q) |
            Q(reason__icontains=q)
        )

    all_list = list(requests_qs)
    pending_count = sum(1 for r in all_list if r.status == 'pending')
    approved_count = sum(1 for r in all_list if r.status == 'approved')
    declined_count = sum(1 for r in all_list if r.status == 'declined')

    if status_filter in ['pending', 'approved', 'declined']:
        requests_qs = requests_qs.filter(status=status_filter)

    return render(request, 'dept-head/dept-head-leave-requests.html', {
        'headed_ministries': headed_ministries,
        'leave_requests': requests_qs,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'declined_count': declined_count,
        'total_requests': len(all_list),
        'search_query': q,
        'status_filter': status_filter,
    })

@login_required
def dept_head_join_requests_view(request):
    """Allows Department Heads to view and approve or decline volunteer requests to join their departments."""
    from schedule_app.models import DepartmentJoinRequest, VolunteerProfile, Ministry
    from schedule_app.utils import log_activity
    from django.db.models import Q
    
    profile = getattr(request.user, 'volunteer_profile', None)
    is_admin = request.user.is_staff or request.user.is_superuser
    
    if profile and profile.headed_ministries.exists():
        headed_ministries = profile.headed_ministries.all()
    elif is_admin:
        headed_ministries = Ministry.objects.all()
    else:
        messages.error(request, "Access restricted to Department Heads.")
        return redirect('user_dashboard')

    # Handle POST actions (Approve / Decline)
    if request.method == 'POST':
        action = request.POST.get('action')
        request_id = request.POST.get('request_id')
        join_req = DepartmentJoinRequest.objects.filter(
            id=request_id,
            ministry__in=headed_ministries
        ).first()

        if join_req:
            volunteer_profile = getattr(join_req.volunteer, 'volunteer_profile', None)
            v_name = join_req.volunteer.get_full_name() or join_req.volunteer.username
            m_name = join_req.ministry.name

            if action == 'approve':
                join_req.status = 'approved'
                join_req.reviewed_at = timezone.now()
                join_req.reviewed_by = request.user
                join_req.save()

                if volunteer_profile:
                    volunteer_profile.ministries.add(join_req.ministry)

                log_activity(
                    request=request,
                    action_type='UPDATE',
                    category='Departments',
                    description=f"Approved request for '{v_name}' to join department '{m_name}'"
                )
                messages.success(request, f"Join request approved! {v_name} is now a member of {m_name}.")

            elif action == 'decline':
                join_req.status = 'declined'
                join_req.reviewed_at = timezone.now()
                join_req.reviewed_by = request.user
                join_req.save()

                log_activity(
                    request=request,
                    action_type='UPDATE',
                    category='Departments',
                    description=f"Declined request for '{v_name}' to join department '{m_name}'"
                )
                messages.info(request, f"Join request declined for {v_name}.")
        else:
            messages.error(request, "Join request not found or access denied.")

        return redirect('dept_head_join_requests')

    # GET: List requests
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all').strip()

    requests_qs = DepartmentJoinRequest.objects.filter(
        ministry__in=headed_ministries
    ).select_related('volunteer', 'volunteer__volunteer_profile', 'volunteer__volunteer_profile__role', 'ministry', 'reviewed_by').prefetch_related('volunteer__volunteer_profile__ministries').order_by('-created_at')

    if q:
        requests_qs = requests_qs.filter(
            Q(volunteer__first_name__icontains=q) |
            Q(volunteer__last_name__icontains=q) |
            Q(volunteer__username__icontains=q) |
            Q(ministry__name__icontains=q) |
            Q(reason__icontains=q)
        )

    all_list = list(requests_qs)
    pending_count = sum(1 for r in all_list if r.status == 'pending')
    approved_count = sum(1 for r in all_list if r.status == 'approved')
    declined_count = sum(1 for r in all_list if r.status == 'declined')

    if status_filter in ['pending', 'approved', 'declined']:
        requests_qs = requests_qs.filter(status=status_filter)

    return render(request, 'dept-head/dept-head-join-requests.html', {
        'headed_ministries': headed_ministries,
        'join_requests': requests_qs,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'declined_count': declined_count,
        'total_requests': len(all_list),
        'search_query': q,
        'status_filter': status_filter,
    })

@login_required
def dept_head_jobs_view(request):
    """Allows Department Heads to create, edit, delete, and assign volunteers & team leaders to specific department jobs/roles."""
    from schedule_app.models import DepartmentJob, VolunteerProfile, Ministry
    
    profile = getattr(request.user, 'volunteer_profile', None)
    is_admin = request.user.is_staff or request.user.is_superuser
    
    if profile and profile.headed_ministries.exists():
        headed_ministries = profile.headed_ministries.all()
    elif is_admin:
        headed_ministries = Ministry.objects.all()
    else:
        messages.error(request, "Access restricted to Department Heads.")
        return redirect('user_dashboard')
        
    # Department Members available to be assigned or made Team Leader
    dept_members = VolunteerProfile.objects.filter(
        ministries__in=headed_ministries
    ).distinct().select_related('user', 'role').prefetch_related('ministries')
    
    # Handle POST Actions
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'save_job':
            job_id = request.POST.get('job_id')
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            ministry_id = request.POST.get('ministry_id')
            team_leader_id = request.POST.get('team_leader_id') or None
            assigned_volunteer_ids = request.POST.getlist('assigned_volunteers')
            
            ministry = headed_ministries.filter(id=ministry_id).first() if ministry_id else headed_ministries.first()
            if not ministry:
                messages.error(request, "No department found.")
                return redirect('dept_head_jobs')
                
            if not title:
                messages.error(request, "Job title is required.")
                return redirect('dept_head_jobs')
                
            team_leader = dept_members.filter(id=team_leader_id).first() if team_leader_id else None
            volunteers_to_assign = list(dept_members.filter(id__in=assigned_volunteer_ids))
            if team_leader and team_leader not in volunteers_to_assign:
                volunteers_to_assign.append(team_leader)
            
            if job_id:
                # Edit
                job = DepartmentJob.objects.filter(id=job_id, ministry__in=headed_ministries).first()
                if job:
                    job.title = title
                    job.description = description
                    job.ministry = ministry
                    job.team_leader = team_leader
                    job.save()
                    job.assigned_volunteers.set(volunteers_to_assign)
                    messages.success(request, f'Job position "{title}" updated successfully.')
            else:
                # Create
                job = DepartmentJob.objects.create(
                    title=title,
                    description=description,
                    ministry=ministry,
                    team_leader=team_leader
                )
                job.assigned_volunteers.set(volunteers_to_assign)
                messages.success(request, f'Job position "{title}" created successfully.')
                
            return redirect('dept_head_jobs')
            
        elif action == 'delete_job':
            job_id = request.POST.get('job_id')
            DepartmentJob.objects.filter(id=job_id, ministry__in=headed_ministries).delete()
            messages.success(request, "Job position deleted successfully.")
            return redirect('dept_head_jobs')
            
    jobs = DepartmentJob.objects.filter(
        ministry__in=headed_ministries
    ).select_related('ministry', 'team_leader__user').prefetch_related('assigned_volunteers__user').order_by('ministry__name', 'title')
    
    total_assigned_count = sum(j.assigned_volunteers.count() for j in jobs)
    total_team_leaders_count = jobs.filter(team_leader__isnull=False).count()
    
    return render(request, 'dept-head/dept-head-jobs.html', {
        'jobs': jobs,
        'headed_ministries': headed_ministries,
        'dept_members': dept_members,
        'total_jobs': jobs.count(),
        'total_assigned_count': total_assigned_count,
        'total_team_leaders_count': total_team_leaders_count,
    })

