from django import forms
from .models import JobModel, InterviewModel

class JobCreationForm(forms.ModelForm):
    class Meta:
        model = JobModel
        fields = ['title', 'description', 'company_name', 'location', 'salary', 'minimum_score']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Software Engineer Intern'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Describe the role, responsibilities, and technical stack...'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., TechInc'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Remote / San Francisco, CA'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 60000'}),
            'minimum_score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'placeholder': 'e.g., 75'}),
        }


class InterviewSchedulingForm(forms.ModelForm):
    class Meta:
        model = InterviewModel
        fields = ['scheduled_time', 'meeting_link', 'notes']
        widgets = {
            'scheduled_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'meeting_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Google Meet or Zoom link'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Bring a physical copy of your resume...'}),
        }