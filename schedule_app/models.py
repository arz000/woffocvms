from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Ministry(models.Model):
    """
    Represents the different departments or roles volunteers can serve in 
    (e.g., Worship Team, Ushers, Greeters).
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    head = models.ForeignKey('VolunteerProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='headed_ministries')

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Ministries"


class Capability(models.Model):
    """
    Represents a specific permission or capability in the system.
    """
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Capabilities"


class Role(models.Model):
    """
    Represents a system role (e.g., System Administrator, Volunteer)
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    badge = models.CharField(max_length=50) # e.g. "Superuser", "Staff"
    theme = models.CharField(max_length=50) # e.g. "red", "amber", "blue"
    capabilities = models.ManyToManyField(Capability, blank=True, related_name='roles')

    def __str__(self):
        return self.name


class VolunteerProfile(models.Model):
    """
    Extends the built-in Django User model to store additional information.
    """
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='volunteer_profile')
    phone_number = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    birthday = models.DateField(null=True, blank=True)
    ministries = models.ManyToManyField(Ministry, blank=True, related_name='volunteers')
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='volunteers')
    
    # Extended Profile Fields
    bio = models.TextField(blank=True, default="No bio provided.")
    country = models.CharField(max_length=100, blank=True)
    city_state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.username})"


class Event(models.Model):
    """
    Represents a specific church service or gathering.
    """
    EVENT_TYPES = [
        ('regular', 'Regular Service'),
        ('scheduled', 'Scheduled Event'),
        ('big', 'Big Event'),
    ]

    name = models.CharField(max_length=200)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, default='regular')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField(blank=True)
    offices = models.ManyToManyField('Ministry', blank=True, related_name='events')

    def __str__(self):
        return f"{self.name} - {self.date}"


class Shift(models.Model):
    """
    Represents a specific role that needs to be filled during an Event.
    """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='shifts')
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE, related_name='shifts')
    job = models.ForeignKey('DepartmentJob', on_delete=models.SET_NULL, null=True, blank=True, related_name='shifts')
    volunteer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='shifts')
    
    # Optional override times (if a shift needs to start earlier than the event)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    def __str__(self):
        status = "Filled" if self.volunteer else "Open"
        return f"{self.ministry.name} for {self.event.name} ({status})"


class DepartmentJob(models.Model):
    """
    Represents specific job positions / roles within a Department / Ministry
    (e.g., Cameraman, Projector Operator, Sound Engineer, Lead Singer).
    """
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE, related_name='jobs')
    team_leader = models.ForeignKey(VolunteerProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='led_jobs')
    assigned_volunteers = models.ManyToManyField(VolunteerProfile, blank=True, related_name='assigned_jobs')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.ministry.name})"

    class Meta:
        ordering = ['title']
        verbose_name = "Department Job"
        verbose_name_plural = "Department Jobs"


class Unavailability(models.Model):
    """
    Represents dates when a volunteer requests to be unavailable/cannot serve (Blackout Dates).
    Requires Department Head review and confirmation.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    ]

    volunteer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unavailabilities')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_unavailabilities')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.volunteer.get_full_name() or self.volunteer.username} unavailable on {self.start_date} ({self.status})"

    class Meta:
        verbose_name_plural = "Unavailabilities"
        ordering = ['start_date']

class ActivityLog(models.Model):
    """
    Logs administrative, user, and security actions across the system.
    """
    ACTION_CHOICES = [
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'),
        ('DELETE', 'Deleted'),
        ('ASSIGN', 'Assigned'),
        ('AUTH', 'Authentication'),
        ('SECURITY', 'Security'),
    ]

    CATEGORY_CHOICES = [
        ('Roles', 'Roles & Permissions'),
        ('Members', 'Members'),
        ('Departments', 'Departments'),
        ('Events', 'Events'),
        ('Shifts', 'Shifts'),
        ('Jobs', 'Department Jobs'),
        ('Auth', 'Authentication'),
        ('General', 'General'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_logs')
    actor_name = models.CharField(max_length=150, blank=True)
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES, default='UPDATE')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='General')
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"

    def __str__(self):
        actor = self.actor_name or (self.user.get_full_name() or self.user.username if self.user else "System")
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {actor}: {self.description[:50]}"



class DepartmentLeaveRequest(models.Model):
    """
    Represents a request submitted by a volunteer to leave a department/ministry,
    which requires review and approval by the Department Head.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    ]

    volunteer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='department_leave_requests')
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE, related_name='leave_requests')
    reason = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_leave_requests')

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Department Leave Request"
        verbose_name_plural = "Department Leave Requests"

    def __str__(self):
        actor = self.volunteer.get_full_name() or self.volunteer.username
        return f"{actor} - {self.ministry.name} ({self.status})"


class DepartmentJoinRequest(models.Model):
    """
    Represents a request submitted by a volunteer to join a department/ministry,
    which requires review and approval by the Department Head.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    ]

    volunteer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='department_join_requests')
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE, related_name='join_requests')
    reason = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_join_requests')

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Department Join Request"
        verbose_name_plural = "Department Join Requests"

    def __str__(self):
        actor = self.volunteer.get_full_name() or self.volunteer.username
        return f"{actor} - Join {self.ministry.name} ({self.status})"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        VolunteerProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.volunteer_profile.save()

