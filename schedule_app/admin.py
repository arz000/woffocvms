from django.contrib import admin
from .models import Ministry, VolunteerProfile, Event, Shift, ActivityLog, Role, Capability

@admin.register(Capability)
class CapabilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'badge', 'theme')
    search_fields = ('name', 'description')
    filter_horizontal = ('capabilities',)


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

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('actor_name', 'action_type', 'category', 'description', 'ip_address', 'created_at')
    list_filter = ('action_type', 'category', 'created_at')
    search_fields = ('actor_name', 'description', 'ip_address', 'user__username')
