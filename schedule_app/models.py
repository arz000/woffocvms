from django.db import models
from django.contrib.auth.models import User

class Member(models.Model):

      ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('MEMBER', 'Member'),
    ]  
      user = models.OneToOneField(User, on_delete=models.CASCADE)
      
      role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='MEMBER'
    )
      
      phone = models.CharField(max_length=20, null=True, blank=True)
      birth_date = models.DateField(null=True, blank=True)
      joined_date = models.DateField(auto_now_add=True, null=True)
      
      def __str__(self):
        return self.user.username

    
class Activity(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='activities', null=True)

    title = models.CharField(max_length=100)
    description = models.TextField()
    activity_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at'] 

    def __str__(self):
        return self.title

class Post(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    title = models.CharField(max_length=150)
    content = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title