from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def smart_date(value):
    if not value:
        return ""

    now = timezone.localtime()
    value = timezone.localtime(value)

    today = now.date()
    post_day = value.date()

    diff = (today - post_day).days

    # Today
    if diff == 0:
        return value.strftime("%#I:%M %p")      # 24-hour format

    # Yesterday
    elif diff == 1:
        return "Yesterday"

    # Within the last week
    elif diff < 7:
        return f"{diff} days ago"

    # Older posts
    return value.strftime("%b %d, %Y")