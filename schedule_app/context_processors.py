from datetime import date
from .models import Event

def upcoming_events_count(request):
    """Injects upcoming event count into every template context for the sidebar badge."""
    try:
        count = Event.objects.filter(date__gte=date.today()).count()
    except Exception:
        count = 0
    return {'upcoming_events_count': count}
