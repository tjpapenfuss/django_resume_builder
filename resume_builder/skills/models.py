# skills/models.py

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db.models import Q
from django.core.exceptions import ValidationError
from jobs.models import JobApplication
import uuid

class Skill(models.Model):
    skill_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="skills")
    category = models.CharField(max_length=255, null=False)
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    years_experience = models.PositiveIntegerField(blank=True, null=True)
    details = models.JSONField(default=dict, blank=True, null=True)
    created_date = models.DateTimeField(default=timezone.now, null=False)
    updated_date = models.DateTimeField(auto_now=True)

    # Skill type options
    SKILL_TYPE_CHOICES = [
        ('Soft', 'Soft Skill'),
        ('Hard', 'Hard Skill'),
        ('Technical', 'Technical Skill'),
        ('Transferable', 'Transferable Skill'),
        ('Other', 'Other Skill')
    ]
    # Skill level options
    SKILL_LEVELS = [
        ('Entry', 'Entry level'),
        ('Intermediate', 'Intermediate level'),
        ('Advanced', 'Advanced level'),
        ('Expert', 'Expert level'),
        ('Mastery', 'Mastery level'),
    ]
    # Common skill categories -- Not mandatory to use. 
    SKILL_CATEGORIES = [
        ('Programming', 'Programming'),
        ('Communication', 'Communication'),
        ('Technology', 'Technology'),
        ('Leadership', 'Leadership'),
        ('Design', 'Design'),
        ('Languages', 'Languages'),
        ('Other', 'Other'),
    ]
    skill_type = models.CharField(max_length=50, blank=True, null=True, choices=SKILL_TYPE_CHOICES)
    skill_level = models.CharField(max_length=255, blank=True, null=True, choices=SKILL_LEVELS)

    class Meta:
        db_table = 'skill'
        constraints = [
            models.UniqueConstraint(fields=['user', 'title'], name='unique_user_title'),
            models.CheckConstraint(
                check=Q(skill_type__in=['Soft', 'Hard', 'Technical', 'Transferable', 'Other']),
                name="valid_skill_type"
            ),
            models.CheckConstraint(
                check=Q(years_experience__gte=0),
                name="non_negative_years_experience"
            ),
            models.CheckConstraint(
                check=Q(skill_level__in=['Entry', 'Intermediate', 'Advanced', 'Expert', 'Mastery']),
                name="valid_skill_level"
            ),
        ]

    def clean(self):
        """Django-level validation (runs before saving via full_clean())"""
        super().clean()
        
        # Only check for duplicate titles if both title and user are set
        if self.title and hasattr(self, 'user') and self.user:
            existing = Skill.objects.filter(
                user=self.user, 
                title=self.title
            ).exclude(skill_id=self.skill_id)
            if existing.exists():
                raise ValidationError({'title': 'You already have a skill with this title.'})

        valid_skill_types = ['Soft', 'Hard', 'Technical', 'Transferable', 'Other']
        valid_skill_levels = ['Entry', 'Intermediate', 'Advanced', 'Expert', 'Mastery']

        if self.skill_type and self.skill_type not in valid_skill_types:
            raise ValidationError({'skill_type': f"Skill type must be one of {valid_skill_types}."})

        if self.skill_level and self.skill_level not in valid_skill_levels:
            raise ValidationError({'skill_level': f"Skill level must be one of {valid_skill_levels}."})

        if self.years_experience is not None and self.years_experience < 0:
            raise ValidationError({'years_experience': "Years of experience must be a non-negative integer."})

    def __str__(self):
        return str(self.title)

    @property
    def experience_count(self):
        """Count of experiences demonstrating this skill"""
        return self.experiences.count()

    @property
    def most_recent_experience(self):
        """Most recent experience demonstrating this skill"""
        return self.experiences.order_by('-date_started', '-created_date').first()

    def get_proficiency_score(self):
        """Calculate a proficiency score based on years of experience and skill level"""
        level_scores = {
            'Entry': 1,
            'Intermediate': 2,
            'Advanced': 3,
            'Expert': 4,
            'Mastery': 5
        }
        
        level_score = level_scores.get(self.skill_level, 1)
        years_score = min((self.years_experience or 0) / 2, 5)  # Cap at 5, 2 years per point
        
        return round((level_score + years_score) / 2, 1)


class ExperienceSkill(models.Model):
    """
    Through model for many-to-many relationship between Experience and Skill.
    Allows us to store additional context about how the skill was used in that experience.
    """
    experience_skill_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    experience = models.ForeignKey('experience.Experience', on_delete=models.CASCADE)  # Correct app name
    skill = models.ForeignKey('Skill', on_delete=models.CASCADE)
    
    # Additional context about this skill in this experience
    proficiency_demonstrated = models.CharField(
        max_length=50, 
        choices=Skill.SKILL_LEVELS,
        blank=True,
        null=True,
        help_text="Level of proficiency demonstrated in this specific experience"
    )
    
    # How prominently this skill featured in the experience
    PROMINENCE_CHOICES = [
        ('primary', 'Primary Skill - Central to the experience'),
        ('secondary', 'Secondary Skill - Important but not central'),
        ('supporting', 'Supporting Skill - Used but not prominent'),
    ]
    prominence = models.CharField(
        max_length=20,
        choices=PROMINENCE_CHOICES,
        default='secondary',
        help_text="How prominently this skill featured in the experience"
    )
    
    # Specific notes about how this skill was used
    usage_notes = models.TextField(
        blank=True,
        help_text="Specific notes about how this skill was applied in this experience"
    )
    
    # When this relationship was established
    created_date = models.DateTimeField(default=timezone.now)
    
    # Track if this was auto-extracted or manually added
    extraction_method = models.CharField(
        max_length=20,
        choices=[
            ('manual', 'Manually Added'),
            ('auto_extracted', 'Automatically Extracted'),
            ('ai_suggested', 'AI Suggested'),
        ],
        default='manual'
    )

    class Meta:
        db_table = 'experience_skill'
        unique_together = ('experience', 'skill')  # Prevent duplicate relationships
        indexes = [
            models.Index(fields=['experience', 'prominence']),
            models.Index(fields=['skill', 'proficiency_demonstrated']),
        ]

    def __str__(self):
        return f"{self.skill.title} in {self.experience.title}"


class SkillAnalysis(models.Model):
    """
    Stores the results of skill gap analysis runs.
    Allows users to reference past analyses and track progress over time.
    """
    analysis_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="skill_analyses"
    )
    
    # When this analysis was run
    created_at = models.DateTimeField(default=timezone.now)
    
    # Snapshot of user's data at time of analysis
    total_experiences_analyzed = models.PositiveIntegerField()
    total_jobs_analyzed = models.PositiveIntegerField()
    total_skills_found = models.PositiveIntegerField()
    new_skills_created = models.PositiveIntegerField(default=0)
    
    # Summary statistics
    total_skill_gaps = models.PositiveIntegerField()
    average_job_match_score = models.FloatField(
        help_text="Average match percentage across all analyzed jobs"
    )
    highest_job_match_score = models.FloatField()
    lowest_job_match_score = models.FloatField()
    
    # Detailed results stored as JSON
    skill_gaps = models.JSONField(
        default=list,
        help_text="List of skill gaps found, ordered by priority"
    )
    job_matches = models.JSONField(
        default=list,
        help_text="Detailed job match analysis results"
    )
    skills_extracted = models.JSONField(
        default=list,
        help_text="List of new skills extracted from experiences"
    )
    
    # Analysis configuration/version for future compatibility
    analyzer_version = models.CharField(max_length=10, default='1.0')
    analysis_parameters = models.JSONField(
        default=dict,
        help_text="Parameters used for this analysis run"
    )
    
    # User notes about this analysis
    user_notes = models.TextField(
        blank=True,
        help_text="User's notes or observations about this analysis"
    )
    
    # Track if user has acted on this analysis
    STATUS_CHOICES = [
        ('fresh', 'Fresh Analysis'),
        ('in_progress', 'User Taking Action'), 
        ('completed', 'User Addressed Gaps'),
        ('archived', 'Archived/Superseded'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='fresh'
    )

    class Meta:
        db_table = 'skill_analysis'
        ordering = ['-created_at']  # Most recent first
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"Skill Analysis for {self.user.username} on {self.created_at.date()}"

    @property 
    def is_recent(self):
        """Check if analysis is less than 7 days old"""
        
        return (timezone.now() - self.created_at).days < 7

    @property
    def staleness_indicator(self):
        """Get staleness indicator for the UI"""
        days_old = (timezone.now() - self.created_at).days
        
        if days_old == 0:
            return "Today"
        elif days_old == 1:
            return "Yesterday"  
        elif days_old < 7:
            return f"{days_old} days ago"
        elif days_old < 30:
            weeks_old = days_old // 7
            return f"{weeks_old} week{'s' if weeks_old > 1 else ''} ago"
        else:
            return f"{days_old} days ago"

    @property
    def top_skill_gaps(self):
        """Get top 5 skill gaps"""
        return self.skill_gaps[:5]

    @property
    def needs_refresh(self):
        """Determine if analysis should be refreshed based on user's current data"""
        from experience.models import Experience  # Correct app name
        
        current_experiences = Experience.objects.filter(user=self.user).count()
        current_jobs = JobApplication.objects.filter(user=self.user).count()
        current_skills = Skill.objects.filter(user=self.user).count()
        
        return (
            current_experiences > self.total_experiences_analyzed + 1 or
            current_jobs > self.total_jobs_analyzed + 2 or  
            current_skills > self.total_skills_found + 3
        )

    def mark_in_progress(self):
        """Mark analysis as being acted upon by user"""
        self.status = 'in_progress'
        self.save(update_fields=['status'])

    def mark_completed(self, user_notes=""):
        """Mark analysis as completed with optional notes"""
        self.status = 'completed'
        if user_notes:
            self.user_notes = user_notes
        self.save(update_fields=['status', 'user_notes'])

    def get_gap_for_skill(self, skill_name):
        """Get specific gap information for a skill name"""
        for gap in self.skill_gaps:
            if gap.get('skill_name', '').lower() == skill_name.lower():
                return gap
        return None

    def get_job_suggestions_for_skill(self, skill_name):
        """Get jobs that require a specific skill"""
        matching_jobs = []
        for job_match in self.job_matches:
            if skill_name.lower() in [s.lower() for s in job_match.get('missing_skills', [])]:
                matching_jobs.append(job_match)
        return matching_jobs


