from django.db import models
from django.conf import settings
from users_app.models import UserModel

class JobModel(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()

    company_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    salary = models.IntegerField()

    created_by = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class ApplicationModel(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    job = models.ForeignKey(JobModel, on_delete=models.CASCADE)
    applicant = models.ForeignKey(UserModel, on_delete=models.SET_NULL, null=True, blank=True)

    cover_letter = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        applicant_name = self.applicant.username if self.applicant else "Anonymous"
        return f"{applicant_name} - {self.job.title}"