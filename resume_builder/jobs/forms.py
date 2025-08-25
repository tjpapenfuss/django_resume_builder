
from django import forms
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import re

class JobURLForm(forms.Form):
    url = forms.URLField(
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://company.com/careers/job-posting',
            'size': 80
        }),
        help_text="Paste the URL of a job posting from a company's career page"
    )
    
    manual_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 15,
            'placeholder': 'If the auto-scraper missed details, copy and paste the full job description here...'
        }),
        help_text="Optional: Paste the full job description text here if the auto-scraper didn't capture everything"
    )
    
    def clean_url(self):
        url = self.cleaned_data['url']
        
        # Basic URL validation
        try:
            validator = URLValidator()
            validator(url)
        except ValidationError:
            raise forms.ValidationError("Please enter a valid URL")
        
        # Check if it looks like a job posting URL
        job_indicators = [
            'job', 'career', 'position', 'opening', 'posting', 
            'greenhouse.io', 'lever.co', 'workday', 'bamboohr'
        ]
        
        if not any(indicator in url.lower() for indicator in job_indicators):
            # Warning but don't fail validation
            pass
        
        return url