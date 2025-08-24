# forms.py
from django import forms
from django.db.models import Q
from .models import Skill


class SkillForm(forms.ModelForm):
    # Extra JSON details fields
    certifications = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'List certifications related to this skill (one per line)',
            'rows': 3
        })
    )

    projects = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'List projects where you applied this skill (one per line)',
            'rows': 3
        })
    )

    # Choice overrides for constraints
    SKILL_TYPES = [
        ('', 'Select skill type'),
        ('Soft', 'Soft'),
        ('Hard', 'Hard'),
        ('Technical', 'Technical'),
        ('Transferable', 'Transferable'),
        ('Other', 'Other'),
    ]

    SKILL_LEVELS = [
        ('', 'Select skill level'),
        ('Entry', 'Entry'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
        ('Expert', 'Expert'),
        ('Mastery', 'Mastery'),
    ]

    # Predefined categories but allow custom input
    category = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter or select category',
            'list': 'category-options'
        })
    )

    skill_type = forms.ChoiceField(
        choices=SKILL_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    skill_level = forms.ChoiceField(
        choices=SKILL_LEVELS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Skill
        fields = ['category', 'skill_type', 'title', 'description', 'skill_level', 'years_experience']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter skill title (e.g., Python, Team Leadership)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description of the skill',
                'rows': 3
            }),
            'years_experience': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Years of experience',
                'min': '0'
            }),
        }

    def __init__(self, *args, **kwargs):
        # Extract user from kwargs if provided (for getting existing categories)
        self.user = kwargs.pop('user', None)
        instance = kwargs.get('instance')
        
        if instance and instance.details:
            initial = kwargs.setdefault('initial', {})
            initial['certifications'] = '\n'.join(instance.details.get('certifications', []))
            initial['projects'] = '\n'.join(instance.details.get('projects', []))

        super().__init__(*args, **kwargs)

        # Required fields
        self.fields['category'].required = True
        self.fields['title'].required = True

        # Labels
        self.fields['category'].label = 'Category'
        self.fields['title'].label = 'Skill Title'
        self.fields['description'].label = 'Description'
        self.fields['skill_type'].label = 'Skill Type'
        self.fields['skill_level'].label = 'Skill Level'
        self.fields['years_experience'].label = 'Years of Experience'
        self.fields['certifications'].label = 'Certifications'
        self.fields['projects'].label = 'Projects'

        # Help text
        self.fields['category'].help_text = 'Select a common category or enter your own'
        self.fields['years_experience'].help_text = 'Enter a non-negative integer'
        self.fields['certifications'].help_text = 'Relevant certifications (one per line)'
        self.fields['projects'].help_text = 'Projects where this skill was applied (one per line)'

    def clean_years_experience(self):
        years = self.cleaned_data.get('years_experience')
        if years is not None and years < 0:
            raise forms.ValidationError("Years of experience must be a non-negative number.")
        return years

    def clean_category(self):
        category = self.cleaned_data.get('category', '').strip()
        if not category:
            raise forms.ValidationError("Category is required.")
        return category

    def save(self, commit=True):
        instance = super().save(commit=False)
        details = {}

        certifications_text = self.cleaned_data.get('certifications', '')
        if certifications_text.strip():
            details['certifications'] = [c.strip() for c in certifications_text.split('\n') if c.strip()]

        projects_text = self.cleaned_data.get('projects', '')
        if projects_text.strip():
            details['projects'] = [p.strip() for p in projects_text.split('\n') if p.strip()]

        instance.details = details

        if commit:
            instance.save()
        return instance

    def get_existing_categories(self):
        """Get categories that the user has already used"""
        if self.user:
            return Skill.objects.filter(user=self.user).values_list('category', flat=True).distinct()
        return []


class SkillFilterForm(forms.Form):
    """Form for filtering and searching skills"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search skills by title, category, or description...',
            'id': 'skill-search'
        })
    )
    
    category = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by category',
            'list': 'filter-category-options'
        })
    )
    
    skill_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + Skill.SKILL_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    skill_level = forms.ChoiceField(
        required=False,
        choices=[('', 'All Levels')] + Skill.SKILL_LEVELS,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Default (Newest First)'),
            ('-created_date', 'Newest First'),
            ('created_date', 'Oldest First'),
            ('title', 'Title A-Z'),
            ('-title', 'Title Z-A'),
            ('category', 'Category A-Z'),
            ('-years_experience', 'Most Experience'),
            ('years_experience', 'Least Experience'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def get_existing_categories(self):
        """Get categories that the user has already used for filtering"""
        if self.user:
            return Skill.objects.filter(user=self.user).values_list('category', flat=True).distinct().order_by('category')
        return []