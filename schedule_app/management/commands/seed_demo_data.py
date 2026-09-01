import random
from datetime import date, timedelta, time
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from schedule_app.models import Ministry, VolunteerProfile, Event, Shift, Role

class Command(BaseCommand):
    help = 'Seeds initial demo data for ministries, users, events, and shifts.'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting data seed...')

        # 1. Create Ministries
        ministries_data = [
            {"name": "Music", "desc": "Worship band and choir"},
            {"name": "Media", "desc": "Audio, visual, and streaming"},
            {"name": "Children's Ministry", "desc": "Sunday school teachers and volunteers"}
        ]
        ministry_objs = {}
        for m in ministries_data:
            obj, _ = Ministry.objects.get_or_create(name=m["name"], defaults={"description": m["desc"]})
            ministry_objs[m["name"]] = obj

        # 2. Get/Create Roles
        volunteer_role = Role.objects.filter(name="Volunteer").first()
        lead_role = Role.objects.filter(name="Department Head").first()

        # 3. Create Users & Profiles
        users_data = [
            ("asmith", "Alex", "Smith", "Music", lead_role),
            ("jdoe", "Jane", "Doe", "Music", volunteer_role),
            ("swilliams", "Sarah", "Williams", "Media", lead_role),
            ("bjohnson", "Bob", "Johnson", "Media", volunteer_role),
            ("pking", "Peter", "King", "Children's Ministry", lead_role),
            ("emiller", "Emily", "Miller", "Children's Ministry", volunteer_role),
        ]
        
        user_objs = {}
        for username, fname, lname, ministry_name, role in users_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": fname,
                    "last_name": lname,
                    "email": f"{username}@example.com"
                }
            )
            if created:
                user.set_password("password123")
                user.save()
            
            profile, _ = VolunteerProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.ministries.add(ministry_objs[ministry_name])
            profile.save()
            user_objs[username] = user

        # 4. Create Events for current month
        today = date.today()
        # Find next Sunday
        days_ahead = 6 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_sunday = today + timedelta(days_ahead)
        
        events_data = [
            {
                "name": "Sunday Service",
                "date": next_sunday,
                "start": time(9, 0),
                "end": time(11, 0)
            },
            {
                "name": "Worship Practice",
                "date": next_sunday - timedelta(days=4), # Wednesday
                "start": time(18, 30),
                "end": time(20, 30)
            },
            {
                "name": "Youth Group",
                "date": next_sunday - timedelta(days=2), # Friday
                "start": time(19, 0),
                "end": time(21, 0)
            },
            {
                "name": "Next Sunday Service",
                "date": next_sunday + timedelta(days=7),
                "start": time(9, 0),
                "end": time(11, 0)
            }
        ]

        event_objs = []
        for e in events_data:
            event, _ = Event.objects.get_or_create(
                name=e["name"],
                date=e["date"],
                defaults={"start_time": e["start"], "end_time": e["end"]}
            )
            event_objs.append(event)

        # 5. Create Shifts for Events
        for event in event_objs:
            # Music shift
            shift1, _ = Shift.objects.get_or_create(event=event, ministry=ministry_objs["Music"])
            shift1.volunteer = user_objs["asmith"]
            shift1.save()

            # Media shift
            shift2, _ = Shift.objects.get_or_create(event=event, ministry=ministry_objs["Media"])
            shift2.volunteer = user_objs["swilliams"]
            shift2.save()
            
            # Children's shift (unassigned for some)
            if "Sunday" in event.name:
                shift3, _ = Shift.objects.get_or_create(event=event, ministry=ministry_objs["Children's Ministry"])
                # Leave volunteer blank sometimes to show "Open" status
                if event.name == "Sunday Service":
                    shift3.volunteer = user_objs["pking"]
                shift3.save()

        self.stdout.write(self.style.SUCCESS('Successfully seeded demo data!'))
