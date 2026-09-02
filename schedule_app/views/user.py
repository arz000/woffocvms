from schedule_app.models import Event
from django.utils import timezone
from django.db.models import Count
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from schedule_app.forms import UserProfileForm

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
    
    context = {}
    if hasattr(request.user, 'volunteer_profile'):
        profile = request.user.volunteer_profile
        is_dept_head = profile.role and profile.role.name == 'Department Head'
        context['is_dept_head'] = is_dept_head
        
        if is_dept_head:
            headed_ministries = profile.headed_ministries.prefetch_related('volunteers__user', 'volunteers__role').all()
            
            # Get all member profiles across headed ministries
            from schedule_app.models import VolunteerProfile
            dept_members = VolunteerProfile.objects.filter(
                ministries__in=headed_ministries
            ).distinct().select_related('user', 'role')
            
            # Get upcoming events for their departments
            today = timezone.now().date()
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
            
    return render(request, 'volunteer/volunteer-dashboard.html', context)

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
    base_query = Event.objects.filter(
        offices__in=headed_ministries,
        date__gte=today
    ).distinct().order_by('date', 'start_time').prefetch_related('offices', 'shifts__volunteer', 'shifts__ministry')
    
    # Annotate each event with filled_count
    def annotate_events(events):
        for event in events:
            event.filled_count = event.shifts.filter(volunteer__isnull=False).count()
        return events
    
    regular_events = annotate_events(list(base_query.filter(event_type='regular')))
    scheduled_events = annotate_events(list(base_query.filter(event_type='scheduled')))
    big_events = annotate_events(list(base_query.filter(event_type='big')))
    
    return render(request, 'dept-head/dept-head-events.html', {
        'regular_events': regular_events,
        'scheduled_events': scheduled_events,
        'big_events': big_events,
    })

@login_required
def dept_head_event_detail_view(request, event_id):
    """Shows shifts for a specific event and allows assigning volunteers via POST."""
    from schedule_app.models import Event, Shift, VolunteerProfile
    
    profile = request.user.volunteer_profile
    headed_ministries = profile.headed_ministries.all()
    
    event = Event.objects.prefetch_related('offices', 'shifts__volunteer', 'shifts__ministry').get(id=event_id)
    
    # Only show shifts for departments this head manages
    dept_shifts = event.shifts.filter(ministry__in=headed_ministries).select_related('ministry', 'volunteer')
    
    # Handle POST to assign a volunteer to a shift
    if request.method == 'POST':
        shift_id = request.POST.get('shift_id')
        volunteer_id = request.POST.get('volunteer_id')
        action = request.POST.get('action', 'assign')
        
        shift = Shift.objects.filter(id=shift_id, ministry__in=headed_ministries).first()
        if shift:
            if action == 'remove':
                shift.volunteer = None
                shift.save()
                messages.success(request, 'Volunteer removed from shift.')
            elif volunteer_id:
                from django.contrib.auth.models import User
                volunteer = User.objects.filter(id=volunteer_id).first()
                if volunteer:
                    shift.volunteer = volunteer
                    shift.save()
                    messages.success(request, f'{volunteer.get_full_name()} assigned successfully.')
        
        return redirect('dept_head_event_detail', event_id=event_id)
    
    # Get available volunteers from their departments
    dept_members = VolunteerProfile.objects.filter(
        ministries__in=headed_ministries
    ).distinct().select_related('user', 'role')
    
    # Group shifts by ministry
    shifts_by_ministry = {}
    for shift in dept_shifts:
        ministry_name = shift.ministry.name
        if ministry_name not in shifts_by_ministry:
            shifts_by_ministry[ministry_name] = []
        shifts_by_ministry[ministry_name].append(shift)
    
    return render(request, 'dept-head/dept-head-event-detail.html', {
        'event': event,
        'shifts_by_ministry': shifts_by_ministry,
        'dept_members': dept_members,
    })

