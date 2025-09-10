from django import forms
from .models import Experience
from employment.models import Employment
from education.models import Education

class ExperienceForm(forms.ModelForm):
    """
    Simplified form for creating/updating Experience objects.
    Includes only essential fields: title, description, experience_type, employment, education.
    """


    class Meta:
        """
        Connects the form to the Experience model.
        Defines which model fields are included and how they're rendered.
        """
        model = Experience
        fields = ['title', 'description', 'experience_type', 'employment', 'education']
        
        # Widgets define how form inputs render in HTML
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter experience title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Detailed description of the experience',
                'rows': 4
            }),
            'experience_type': forms.Select(attrs={'class': 'form-control'}),
            'employment': forms.Select(attrs={'class': 'form-control'}),
            'education': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        """
        Customizes initialization:
        - Populates extra fields from `details` JSON if editing an existing instance.
        - Filters Employment/Education dropdowns so user only sees their own records.
        """
        self.user = kwargs.pop('user', None)  # Pass user explicitly to filter choices
        instance = kwargs.get('instance')
        
        # No extra fields to pre-fill in simplified form
        
        # Call ModelForm init
        super().__init__(*args, **kwargs)
        
        # Filter dropdowns to only show this user's Employment/Education
        if self.user:
            self.fields['employment'].queryset = Employment.objects.filter(
                user=self.user
            ).order_by('-date_started', 'company_name')
            self.fields['education'].queryset = Education.objects.filter(
                user=self.user
            ).order_by('-date_started', 'institution_name')
        else:
            self.fields['employment'].queryset = Employment.objects.none()
            self.fields['education'].queryset = Education.objects.none()
        
        # Add "Not linked..." as a blank choice
        self.fields['employment'].empty_label = "Not linked to employment"
        self.fields['education'].empty_label = "Not linked to education"
        
        # Set required/optional fields
        self.fields['title'].required = True
        self.fields['description'].required = True
        
        # Customize labels & help text
        self.fields['employment'].help_text = 'Optionally link this to a job'
        self.fields['education'].help_text = 'Optionally link this to education (project/thesis/etc.)'

    def clean(self):
        """
        Extra validation rules for the form:
        - Can't link to both Employment and Education at the same time.
        """
        cleaned_data = super().clean()
        employment = cleaned_data.get('employment')
        education = cleaned_data.get('education')

        if employment and education:
            raise forms.ValidationError("Experience cannot be linked to both employment and education. Please select only one.")

        return cleaned_data

    def save(self, commit=True):
        """
        Custom save method for simplified form - just saves the basic model fields
        """
        instance = super().save(commit=False)
        
        # Set default values for fields not in the form
        if not instance.details:
            instance.details = {}
        if not instance.skills_used:
            instance.skills_used = []
        if not instance.tags:
            instance.tags = []
        if not instance.visibility:
            instance.visibility = 'public'
        
        if commit:
            instance.save()
        
        return instance