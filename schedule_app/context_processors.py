from datetime import date
from .models import Event

def upcoming_events_count(request):
    """Injects upcoming event count into every template context for the sidebar badge."""
    try:
        count = Event.objects.filter(date__gte=date.today()).count()
    except Exception:
        count = 0
    return {'upcoming_events_count': count}

def pending_leave_requests_count(request):
    """Injects pending department leave requests count for Department Heads into template contexts."""
    try:
        if request.user.is_authenticated:
            profile = getattr(request.user, 'volunteer_profile', None)
            from .models import DepartmentLeaveRequest
            if profile and profile.headed_ministries.exists():
                count = DepartmentLeaveRequest.objects.filter(
                    ministry__in=profile.headed_ministries.all(),
                    status='pending'
                ).count()
                return {'pending_leave_requests_count': count}
            elif request.user.is_staff or request.user.is_superuser:
                count = DepartmentLeaveRequest.objects.filter(status='pending').count()
                return {'pending_leave_requests_count': count}
    except Exception:
        pass
    return {'pending_leave_requests_count': 0}

def pending_join_requests_count(request):
    """Injects pending department join requests count for Department Heads into template contexts."""
    try:
        if request.user.is_authenticated:
            profile = getattr(request.user, 'volunteer_profile', None)
            from .models import DepartmentJoinRequest
            if profile and profile.headed_ministries.exists():
                count = DepartmentJoinRequest.objects.filter(
                    ministry__in=profile.headed_ministries.all(),
                    status='pending'
                ).count()
                return {'pending_join_requests_count': count}
            elif request.user.is_staff or request.user.is_superuser:
                count = DepartmentJoinRequest.objects.filter(status='pending').count()
                return {'pending_join_requests_count': count}
    except Exception:
        pass
    return {'pending_join_requests_count': 0}

def pending_unavailability_requests_count(request):
    """Injects pending unavailable date requests count for Department Heads into template contexts."""
    try:
        if request.user.is_authenticated:
            profile = getattr(request.user, 'volunteer_profile', None)
            from .models import Unavailability, VolunteerProfile
            today = date.today()
            if profile and profile.headed_ministries.exists():
                headed_ministries = profile.headed_ministries.all()
                dept_member_ids = VolunteerProfile.objects.filter(
                    ministries__in=headed_ministries
                ).values_list('user_id', flat=True)
                count = Unavailability.objects.filter(
                    volunteer_id__in=dept_member_ids,
                    status='pending',
                    start_date__gte=today
                ).count()
                return {'pending_unavailability_requests_count': count}
            elif request.user.is_staff or request.user.is_superuser:
                count = Unavailability.objects.filter(status='pending', start_date__gte=today).count()
                return {'pending_unavailability_requests_count': count}
    except Exception:
        pass
    return {'pending_unavailability_requests_count': 0}



