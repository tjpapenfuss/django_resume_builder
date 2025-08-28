from django import forms
from .models import Experience
from employment.models import Employment
from education.models import Education

class ExperienceForm(forms.ModelForm):
    """
    A form for creating/updating Experience objects.
    Includes both model fields (title, description, etc.)
    and custom fields that map into JSON (details, skills, tags).
    """

    # --- AI Analysis field ---
    analyze_with_ai = forms.BooleanField(
        required=False,
        initial=True,  # Default to checked
        widget=forms.CheckboxInput(attrs={
            'class': 'ai-checkbox'
        }),
        help_text='Let AI analyze your experience and suggest skills to add to your profile'
    )

    # --- Extra fields that are stored inside the `details` JSONField ---
    outcomes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Describe the outcomes, results, or impact (one per line)',
            'rows': 3
        })
    )
    
    challenges = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Key challenges faced and how they were overcome (one per line)',
            'rows': 3
        })
    )
    
    tools_used = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Specific tools, software, or technologies used (one per line)',
            'rows': 3
        })
    )
    
    team_size = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., "5 people" or "Solo project"'
        })
    )
    
    budget = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., "$50,000" or "No budget"'
        })
    )
    
    links = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Relevant links (GitHub, portfolio, documentation, etc.) - one per line',
            'rows': 2
        })
    )
    
    # --- Skills/tags (map to JSON arrays in Experience model) ---
    skills_used_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'List relevant skills and technologies (one per line)',
            'rows': 3
        })
    )
    
    tags_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Tags for categorizing (e.g., data-engineering, leadership) - one per line',
            'rows': 2
        })
    )

    class Meta:
        """
        Connects the form to the Experience model.
        Defines which model fields are included and how they're rendered.
        """
        model = Experience
        fields = ['title', 'description', 'experience_type', 'employment', 'education', 
                 'date_started', 'date_finished', 'visibility']
        
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
            'date_started': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_finished': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'visibility': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        """
        Customizes initialization:
        - Populates extra fields from `details` JSON if editing an existing instance.
        - Filters Employment/Education dropdowns so user only sees their own records.
        """
        self.user = kwargs.pop('user', None)  # Pass user explicitly to filter choices
        instance = kwargs.get('instance')
        
        # Pre-fill extra fields from instance.details if editing
        if instance and instance.details:
            initial = kwargs.setdefault('initial', {})
            initial['outcomes'] = '\n'.join(instance.details.get('outcomes', []))
            initial['challenges'] = '\n'.join(instance.details.get('challenges', []))
            initial['tools_used'] = '\n'.join(instance.details.get('tools_used', []))
            initial['team_size'] = instance.details.get('team_size', '')
            initial['budget'] = instance.details.get('budget', '')
            initial['links'] = '\n'.join(instance.details.get('links', []))
            initial['skills_used_text'] = '\n'.join(instance.skills_used or [])
            initial['tags_text'] = '\n'.join(instance.tags or [])
            # Don't default AI analysis to true for existing experiences
            initial['analyze_with_ai'] = False
        
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
        self.fields['date_finished'].required = False
        
        # Customize labels & help text
        self.fields['date_finished'].help_text = 'Leave blank if this is ongoing'
        self.fields['employment'].help_text = 'Optionally link this to a job'
        self.fields['education'].help_text = 'Optionally link this to education (project/thesis/etc.)'
        self.fields['outcomes'].help_text = 'Quantifiable results, metrics, achievements'
        self.fields['challenges'].help_text = 'Problems solved, obstacles overcome'
        self.fields['tools_used'].help_text = 'Specific software, frameworks, methodologies'
        self.fields['skills_used_text'].help_text = 'Skills developed or demonstrated'
        self.fields['tags_text'].help_text = 'For filtering when generating targeted resumes'

    def clean(self):
        """
        Extra validation rules for the form:
        - Can't link to both Employment and Education at the same time.
        - Start date must be before End date.
        """
        cleaned_data = super().clean()
        employment = cleaned_data.get('employment')
        education = cleaned_data.get('education')
        date_started = cleaned_data.get('date_started')
        date_finished = cleaned_data.get('date_finished')

        if employment and education:
            raise forms.ValidationError("Experience cannot be linked to both employment and education. Please select only one.")

        if date_started and date_finished and date_started > date_finished:
            raise forms.ValidationError("Start date cannot be after end date.")

        return cleaned_data

    def save(self, commit=True):
        """
        Custom save method:
        - Converts form textarea inputs into structured JSON (lists/strings).
        - Stores extra details into Experience.details.
        - Normalizes skills_used and tags into lists.
        """
        instance = super().save(commit=False)
        
        details = {}

        # Convert multi-line text into list for outcomes, challenges, tools, links
        outcomes_text = self.cleaned_data.get('outcomes', '')
        if outcomes_text.strip():
            details['outcomes'] = [o.strip() for o in outcomes_text.split('\n') if o.strip()]

        challenges_text = self.cleaned_data.get('challenges', '')
        if challenges_text.strip():
            details['challenges'] = [c.strip() for c in challenges_text.split('\n') if c.strip()]

        tools_text = self.cleaned_data.get('tools_used', '')
        if tools_text.strip():
            details['tools_used'] = [t.strip() for t in tools_text.split('\n') if t.strip()]

        links_text = self.cleaned_data.get('links', '')
        if links_text.strip():
            details['links'] = [l.strip() for l in links_text.split('\n') if l.strip()]

        # Single-value fields (team size, budget)
        team_size = self.cleaned_data.get('team_size', '')
        if team_size.strip():
            details['team_size'] = team_size.strip()
        
        budget = self.cleaned_data.get('budget', '')
        if budget.strip():
            details['budget'] = budget.strip()
        
        # Save the details JSON into the model
        instance.details = details
        
        # Convert textarea into lists for skills and tags
        skills_text = self.cleaned_data.get('skills_used_text', '')
        instance.skills_used = [s.strip() for s in skills_text.split('\n') if s.strip()] if skills_text.strip() else []
        
        tags_text = self.cleaned_data.get('tags_text', '')
        instance.tags = [t.strip().lower() for t in tags_text.split('\n') if t.strip()] if tags_text.strip() else []
        
        if commit:
            instance.save()
        
        return instance