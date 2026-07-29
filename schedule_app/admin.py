from django.contrib import admin
from . models import Member, Activity, Post

# Register your models here.
admin.site.register(Member)
admin.site.register(Activity)
admin.site.register(Post)