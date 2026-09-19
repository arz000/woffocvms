from schedule_app.models import ActivityLog

def get_client_ip(request):
    """Safely extracts client IP address from the request."""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def log_activity(request=None, user=None, action_type='UPDATE', category='General', description='', ip_address=None):
    """
    Safely creates an ActivityLog entry.
    Can accept either `request` (extracting user & IP) or `user` directly.
    """
    try:
        actor_user = None
        actor_name = ""
        ip_addr = ip_address

        if request:
            ip_addr = get_client_ip(request) or ip_address
            if hasattr(request, 'user') and request.user.is_authenticated:
                actor_user = request.user
                full_name = request.user.get_full_name()
                actor_name = full_name if full_name else request.user.username
        
        if not actor_user and user and user.is_authenticated:
            actor_user = user
            full_name = user.get_full_name()
            actor_name = full_name if full_name else user.username

        if not actor_name:
            actor_name = "System"

        ActivityLog.objects.create(
            user=actor_user,
            actor_name=actor_name,
            action_type=action_type,
            category=category,
            description=description,
            ip_address=ip_addr
        )
    except Exception as e:
        # Never crash the main request flow if logging fails
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to log activity: {e}")
