from django.contrib import admin
from . models import Member, Activity, Post, Like, Comment

# Register your models here.
admin.site.register(Member)
admin.site.register(Activity)
admin.site.register(Post)
admin.site.register(Like)
admin.site.register(Comment)