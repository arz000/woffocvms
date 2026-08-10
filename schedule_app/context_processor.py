from .models import Notification

def notifications(request):

    if request.user.is_authenticated:

        notifications = Notification.objects.filter(
            recipient=request.user
        ).order_by('-created_at')

        unread_notifications = notifications.filter(
            is_read=False
        ).count()

        return {
            'notifications': notifications,
            'unread_notifications': unread_notifications,
        }

    return {}