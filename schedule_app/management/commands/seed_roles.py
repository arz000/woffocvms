from django.core.management.base import BaseCommand
from schedule_app.models import Role, Capability

class Command(BaseCommand):
    help = 'Seeds initial roles and capabilities into the database.'

    def handle(self, *args, **kwargs):
        # Capabilities
        caps_data = [
            {"name": "Manage Users", "description": "Can add, edit, or disable user accounts."},
            {"name": "Manage Roles", "description": "Can create and assign system roles."},
            {"name": "System Settings", "description": "Access to global application configurations."},
            {"name": "All Departments", "description": "Can view and manage every department."},
            {"name": "Create Events", "description": "Can create new church events."},
            {"name": "Manage Schedules", "description": "Can create and modify events and rosters."},
            {"name": "View All Members", "description": "Can view the entire member directory."},
            {"name": "Assign Volunteers", "description": "Can schedule volunteers for their department."},
            {"name": "Approve Requests", "description": "Can approve or deny swap/time-off requests."},
            {"name": "Department View Only", "description": "Limited to viewing their specific department."},
            {"name": "View Schedule", "description": "Basic access to view their upcoming schedule."},
            {"name": "Update Availability", "description": "Can block out dates they are unavailable."},
        ]

        caps_objs = {}
        for c in caps_data:
            obj, created = Capability.objects.get_or_create(name=c['name'], defaults={"description": c['description']})
            caps_objs[c['name']] = obj

        # Roles
        roles_data = [
            {
                "name": "System Administrator",
                "description": "Full access to all settings, users, events, and departments.",
                "badge": "Superuser",
                "theme": "red",
                "caps": ["Manage Users", "Manage Roles", "System Settings", "All Departments"]
            },
            {
                "name": "Service Coordinator",
                "description": "Can create and manage schedules, events, and rosters.",
                "badge": "Staff",
                "theme": "amber",
                "caps": ["Create Events", "Manage Schedules", "View All Members"]
            },
            {
                "name": "Department Head",
                "description": "Can manage their specific department's roster and assignments.",
                "badge": "Lead",
                "theme": "blue",
                "caps": ["Assign Volunteers", "Approve Requests", "Department View Only"]
            },
            {
                "name": "Volunteer",
                "description": "Basic access to view schedule and accept/decline requests.",
                "badge": "Default",
                "theme": "emerald",
                "caps": ["View Schedule", "Update Availability"]
            }
        ]

        for r in roles_data:
            role, created = Role.objects.get_or_create(
                name=r['name'],
                defaults={
                    "description": r['description'],
                    "badge": r['badge'],
                    "theme": r['theme']
                }
            )
            
            # Clear existing to ensure clean state if re-run
            role.capabilities.clear()
            for c_name in r['caps']:
                role.capabilities.add(caps_objs[c_name])
            
            role.save()

        self.stdout.write(self.style.SUCCESS('Successfully seeded Roles and Capabilities!'))
