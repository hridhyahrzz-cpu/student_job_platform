from django.contrib.auth.models import User
from django.db import models


class UserModel(User):
    USER_TYPES = (
        ("student", "Student"),
        ("recruiter", "Recruiter"),
    )

    user_type = models.CharField(max_length=20, choices=USER_TYPES)


class Profile(models.Model):
    user = models.OneToOneField(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='profile'
    )

    full_name = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    bio = models.TextField(blank=True)

    score = models.IntegerField(default=0)

    def __str__(self):
        return f"Profile for {self.user.username}"