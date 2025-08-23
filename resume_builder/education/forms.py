# forms.py
from django import forms
from .models import Education
import json

class EducationForm(forms.ModelForm):
    # Additional fields that will be stored in the details JSON field
    certifications = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'List any certifications earned (one per line)',
            'rows': 3
        })
    )
    
    courses = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'List relevant courses or coursework (one per line)',
            'rows': 3
        })
    )
    
    activities = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Clubs, organizations, activities, honors, awards, etc.',
            'rows': 3
        })
    )
    
    additional_info = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Any additional information about your education',
            'rows': 3
        })
    )

    class Meta:
        model = Education
        fields = ['institution_name', 'location', 'major', 'minor', 'gpa', 'date_started', 'date_finished']
        widgets = {
            'institution_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter institution name'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter location (City, State/Country)'
            }),
            'major': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter major/degree program'
            }),
            'minor': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter minor (if applicable)'
            }),
            'gpa': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter GPA (optional)',
                'step': '0.01',
                'min': '0',
                'max': '4'
            }),
            'date_started': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'date_finished': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }

    def __init__(self, *args, **kwargs):
        # Extract details data if editing an existing education entry
        instance = kwargs.get('instance')
        if instance and instance.details:
            initial = kwargs.setdefault('initial', {})
            initial['certifications'] = '\n'.join(instance.details.get('certifications', []))
            initial['courses'] = '\n'.join(instance.details.get('courses', []))
            initial['activities'] = instance.details.get('activities', '')
            initial['additional_info'] = instance.details.get('additional_info', '')
        
        super().__init__(*args, **kwargs)
        
        # Make institution_name required
        self.fields['institution_name'].required = True
        
        # Make GPA and date_finished optional
        self.fields['gpa'].required = False
        self.fields['date_finished'].required = False
        
        # Add labels
        self.fields['institution_name'].label = 'Institution Name'
        self.fields['location'].label = 'Location'
        self.fields['major'].label = 'Major/Degree Program'
        self.fields['minor'].label = 'Minor'
        self.fields['gpa'].label = 'GPA (Optional)'
        self.fields['date_started'].label = 'Start Date'
        self.fields['date_finished'].label = 'End Date'
        self.fields['certifications'].label = 'Certifications'
        self.fields['courses'].label = 'Relevant Courses'
        self.fields['activities'].label = 'Activities & Honors'
        self.fields['additional_info'].label = 'Additional Information'
        
        # Add help text
        self.fields['gpa'].help_text = 'Enter GPA on a 4.0 scale (optional)'
        self.fields['date_finished'].help_text = 'Leave blank if you are currently enrolled'
        self.fields['certifications'].help_text = 'List certifications earned during or related to this education (one per line)'
        self.fields['courses'].help_text = 'List relevant or notable courses (one per line)'
        self.fields['activities'].help_text = 'Include clubs, organizations, honors, awards, leadership roles, etc.'
        
        # Remove required attribute from optional field widgets
        self.fields['gpa'].widget.attrs.pop('required', None)
        self.fields['date_finished'].widget.attrs.pop('required', None)

    def clean(self):
        cleaned_data = super().clean()
        date_started = cleaned_data.get('date_started')
        date_finished = cleaned_data.get('date_finished')
        gpa = cleaned_data.get('gpa')

        # Validate date range
        if date_started and date_finished:
            if date_started > date_finished:
                raise forms.ValidationError("Start date cannot be after end date.")
        
        # Validate GPA range
        if gpa is not None and (gpa < 0 or gpa > 4):
            self.add_error('gpa', 'GPA must be between 0.0 and 4.0')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Prepare details dictionary
        details = {}
        
        # Handle certifications (convert textarea to list)
        certifications_text = self.cleaned_data.get('certifications', '')
        if certifications_text.strip():
            details['certifications'] = [cert.strip() for cert in certifications_text.split('\n') if cert.strip()]
        
        # Handle courses (convert textarea to list)
        courses_text = self.cleaned_data.get('courses', '')
        if courses_text.strip():
            details['courses'] = [course.strip() for course in courses_text.split('\n') if course.strip()]
        
        # Handle activities (store as text)
        activities_text = self.cleaned_data.get('activities', '')
        if activities_text.strip():
            details['activities'] = activities_text.strip()
        
        # Handle additional info (store as text)
        additional_info_text = self.cleaned_data.get('additional_info', '')
        if additional_info_text.strip():
            details['additional_info'] = additional_info_text.strip()
        
        # Save details to the instance
        instance.details = details
        
        if commit:
            instance.save()
        
        return instance