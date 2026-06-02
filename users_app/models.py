from django.contrib.auth.models import User
from django.db import models


class UserModel(User):
    USER_TYPES = (
        ("student", "Student"),
        ("recruiter", "Recruiter"),
    )

    user_type = models.CharField(max_length=20, choices=USER_TYPES)