from django.contrib import admin
from .models import Ministry, VolunteerProfile, Event, Shift

@admin.register(Ministry)
class MinistryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(VolunteerProfile)
class VolunteerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone_number')
    filter_horizontal = ('ministries',)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'start_time', 'end_time')
    list_filter = ('date',)
    search_fields = ('name',)

@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('ministry', 'event', 'volunteer', 'start_time', 'end_time')
    list_filter = ('event', 'ministry', 'volunteer')
    search_fields = ('ministry__name', 'event__name', 'volunteer__username', 'volunteer__first_name')
