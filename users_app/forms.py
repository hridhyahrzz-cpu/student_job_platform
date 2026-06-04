from django import forms
from .models import Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'full_name',
            'phone_number',
            'email',
            'resume',
            'bio',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def clean_resume(self):
        resume = self.cleaned_data.get('resume')
        if resume:
            if resume.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Resume file size must be under 5 MB.')
            valid_extensions = ['.pdf', '.doc', '.docx']
            if not any(resume.name.lower().endswith(ext) for ext in valid_extensions):
                raise forms.ValidationError('Resume must be a PDF, DOC, or DOCX file.')
        return resume
