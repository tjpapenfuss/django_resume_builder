# forms.py - Add this to your existing forms.py
from django import forms
from .models import Employment
import json

class EmploymentForm(forms.ModelForm):
    # Additional fields that will be stored in the details JSON field
    responsibilities = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'List key responsibilities and duties (one per line)',
            'rows': 4
        })
    )
    
    achievements = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'List major achievements and accomplishments (one per line)',
            'rows': 3
        })
    )
    
    skills_used = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'List skills, technologies, and tools used (one per line)',
            'rows': 3
        })
    )
    
    salary = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., $65,000 - $75,000 or Competitive'
        })
    )
    
    employment_type = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Select employment type'),
            ('full_time', 'Full-time'),
            ('part_time', 'Part-time'),
            ('contract', 'Contract'),
            ('internship', 'Internship'),
            ('freelance', 'Freelance'),
            ('temporary', 'Temporary'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    supervisor = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Supervisor or manager name'
        })
    )
    
    reason_for_leaving = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Brief reason for leaving (optional)',
            'rows': 2
        })
    )

    class Meta:
        model = Employment
        fields = ['company_name', 'location', 'title', 'description', 'date_started', 'date_finished']
        widgets = {
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter company name'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter location (City, State/Country)'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter job title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description of the role',
                'rows': 3
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
        # Extract details data if editing an existing employment entry
        instance = kwargs.get('instance')
        if instance and instance.details:
            initial = kwargs.setdefault('initial', {})
            initial['responsibilities'] = '\n'.join(instance.details.get('responsibilities', []))
            initial['achievements'] = '\n'.join(instance.details.get('achievements', []))
            initial['skills_used'] = '\n'.join(instance.details.get('skills_used', []))
            initial['salary'] = instance.details.get('salary', '')
            initial['employment_type'] = instance.details.get('employment_type', '')
            initial['supervisor'] = instance.details.get('supervisor', '')
            initial['reason_for_leaving'] = instance.details.get('reason_for_leaving', '')
        
        super().__init__(*args, **kwargs)
        
        # Make company_name and title required
        self.fields['company_name'].required = True
        self.fields['title'].required = True
        
        # Make date_finished optional for current jobs
        self.fields['date_finished'].required = False
        
        # Add labels
        self.fields['company_name'].label = 'Company Name'
        self.fields['location'].label = 'Location'
        self.fields['title'].label = 'Job Title'
        self.fields['description'].label = 'Job Description'
        self.fields['date_started'].label = 'Start Date'
        self.fields['date_finished'].label = 'End Date'
        self.fields['responsibilities'].label = 'Key Responsibilities'
        self.fields['achievements'].label = 'Achievements & Accomplishments'
        self.fields['skills_used'].label = 'Skills & Technologies'
        self.fields['salary'].label = 'Salary/Compensation'
        self.fields['employment_type'].label = 'Employment Type'
        self.fields['supervisor'].label = 'Supervisor/Manager'
        self.fields['reason_for_leaving'].label = 'Reason for Leaving'
        
        # Add help text
        self.fields['date_finished'].help_text = 'Leave blank if this is your current position'
        self.fields['responsibilities'].help_text = 'List your main job duties and responsibilities (one per line)'
        self.fields['achievements'].help_text = 'Include quantifiable results, awards, promotions, etc. (one per line)'
        self.fields['skills_used'].help_text = 'List relevant skills, software, technologies, tools used (one per line)'
        self.fields['salary'].help_text = 'Optional - can include range, benefits, or just "Competitive"'
        self.fields['reason_for_leaving'].help_text = 'Brief, professional reason (optional)'
        
        # Remove required attribute from optional field widgets
        self.fields['date_finished'].widget.attrs.pop('required', None)

    def clean(self):
        cleaned_data = super().clean()
        date_started = cleaned_data.get('date_started')
        date_finished = cleaned_data.get('date_finished')

        # Validate date range
        if date_started and date_finished:
            if date_started > date_finished:
                raise forms.ValidationError("Start date cannot be after end date.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Prepare details dictionary
        details = {}
        
        # Handle responsibilities (convert textarea to list)
        responsibilities_text = self.cleaned_data.get('responsibilities', '')
        if responsibilities_text.strip():
            details['responsibilities'] = [resp.strip() for resp in responsibilities_text.split('\n') if resp.strip()]
        
        # Handle achievements (convert textarea to list)
        achievements_text = self.cleaned_data.get('achievements', '')
        if achievements_text.strip():
            details['achievements'] = [ach.strip() for ach in achievements_text.split('\n') if ach.strip()]
        
        # Handle skills (convert textarea to list)
        skills_text = self.cleaned_data.get('skills_used', '')
        if skills_text.strip():
            details['skills_used'] = [skill.strip() for skill in skills_text.split('\n') if skill.strip()]
        
        # Handle other single-value fields
        salary = self.cleaned_data.get('salary', '')
        if salary.strip():
            details['salary'] = salary.strip()
        
        employment_type = self.cleaned_data.get('employment_type', '')
        if employment_type:
            details['employment_type'] = employment_type
        
        supervisor = self.cleaned_data.get('supervisor', '')
        if supervisor.strip():
            details['supervisor'] = supervisor.strip()
        
        reason_for_leaving = self.cleaned_data.get('reason_for_leaving', '')
        if reason_for_leaving.strip():
            details['reason_for_leaving'] = reason_for_leaving.strip()
        
        # Save details to the instance
        instance.details = details
        
        if commit:
            instance.save()
        
        return instance