from django import forms
from .models import JobModel

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