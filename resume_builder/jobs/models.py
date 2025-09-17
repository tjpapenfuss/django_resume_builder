# models.py

from django.db import models
from django.contrib.auth.models import User
import uuid
from django.conf import settings


class JobPosting(models.Model):
    # Basic relational fields for filtering/searching
    job_posting_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(unique=True, max_length=500)
    company_name = models.CharField(max_length=200, db_index=True)
    job_title = models.CharField(max_length=300, db_index=True)
    location = models.CharField(max_length=200, blank=True)
    remote_ok = models.BooleanField(default=False)
    
    # Metadata
    scraped_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    scraping_success = models.BooleanField(default=True)
    scraping_error = models.TextField(blank=True)
    
    # All the flexible job data stored as JSON
    raw_json = models.JSONField(default=dict)
    
    # User tracking
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='job_postings')
    
    class Meta:
        ordering = ['-scraped_at']
        indexes = [
            models.Index(fields=['company_name', 'job_title']),
            models.Index(fields=['scraped_at']),
        ]
        db_table = 'job_posting'
    
    def __str__(self):
        return f"{self.job_title} at {self.company_name}"

    def get_user_experiences(self, user, limit=None):
        """Get experiences that user has created/linked for this job"""
        from jobs.models import JobExperience
        
        job_experiences = JobExperience.objects.filter(
            user=user,
            job_posting=self
        ).select_related('experience').order_by('-match_score', '-created_date')
        
        experiences = [je.experience for je in job_experiences]
        
        if limit:
            return experiences[:limit]
        
        return experiences

    def get_quick_added_experiences(self, user):
        """Get experiences created specifically for this job via quick add"""
        from jobs.models import JobExperience
        
        return JobExperience.objects.filter(
            user=user,
            job_posting=self,
            relevance='created_for',
            creation_source='quick_add'
        ).select_related('experience').order_by('-created_date')

    def get_experience_coverage(self, user):
        """Get statistics about experience coverage for this job's skill gaps"""
        from jobs.models import JobExperience
        
        job_experiences = JobExperience.objects.filter(
            user=user,
            job_posting=self
        )
        
        covered_skills = set()
        for job_exp in job_experiences:
            covered_skills.update(job_exp.target_skills or [])
        
        # You would compare this to required skills from job analysis
        # This is just a basic implementation
        return {
            'total_experiences': job_experiences.count(),
            'covered_skills': list(covered_skills),
            'coverage_count': len(covered_skills)
        }
    
    @property
    def required_skills(self):
        """Extract required skills from JSON"""
        return self.raw_json.get('parsed_requirements', {}).get('required_skills', [])
    
    @property
    def preferred_skills(self):
        """Extract preferred skills from JSON"""
        return self.raw_json.get('parsed_requirements', {}).get('preferred_skills', [])
    
    @property
    def all_skills(self):
        """Get all skills mentioned in the job"""
        return self.required_skills + self.preferred_skills
    
    @property
    def experience_requirements(self):
        """Extract experience requirements"""
        return self.raw_json.get('parsed_requirements', {}).get('experience_years', '')
    
    @property
    def key_requirements(self):
        """Extract specific requirements for matching"""
        return self.raw_json.get('parsed_requirements', {}).get('specific_requirements', [])

    @property
    def ai_analysis(self):
        """Extract AI-powered analysis from JSON"""
        return self.raw_json.get('ai_analysis', {})

    @property
    def ai_required_skills(self):
        """Get AI-extracted required skills"""
        return self.ai_analysis.get('required_skills', [])

    @property
    def ai_preferred_skills(self):
        """Get AI-extracted preferred skills"""
        return self.ai_analysis.get('preferred_skills', [])

    @property
    def ai_experience_requirements(self):
        """Get AI-extracted experience requirements"""
        return self.ai_analysis.get('experience_years', '')
        
    @property
    def ai_technologies(self):
        """Extract AI-identified technologies from JSON"""
        return self.ai_analysis.get('technologies_mentioned', [])

    @property
    def has_ai_analysis(self):
        """Check if AI analysis has been performed"""
        return 'ai_analysis' in self.raw_json and bool(self.raw_json['ai_analysis'])

class JobApplication(models.Model):
    """Track user applications to specific jobs"""
    STATUS_CHOICES = [
        ('saved', 'Saved for Later'),
        ('interested', 'Interested'),
        ('applied', 'Applied'),
        ('phone_screen', 'Phone Screen'),
        ('interview', 'Interview'),
        ('offer', 'Offer Received'),
        ('rejected', 'Rejected'),
        ('declined', 'Declined Offer'),
    ]
    job_application_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='job_applications')
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='saved')
    applied_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    resume_version_used = models.CharField(max_length=100, blank=True)  # Track which resume was used
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'job_posting')
        ordering = ['-updated_at']
        db_table = 'job_application'

    def __str__(self):
        return f"{self.user.username} - {self.job_posting.job_title} ({self.status})"


class JobExperience(models.Model):
    """
    Links experiences to specific job applications.
    Tracks which experiences were created for or are relevant to specific jobs.
    """
    job_experience_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='linked_experiences')
    experience = models.ForeignKey('experience.Experience', on_delete=models.CASCADE, related_name='linked_jobs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # How this experience relates to the job
    RELEVANCE_CHOICES = [
        ('created_for', 'Created Specifically For This Job'),
        ('highly_relevant', 'Highly Relevant'),
        ('somewhat_relevant', 'Somewhat Relevant'),
        ('manually_linked', 'Manually Linked by User'),
    ]
    relevance = models.CharField(
        max_length=20,
        choices=RELEVANCE_CHOICES,
        default='highly_relevant'
    )
    
    # Which skill(s) this experience demonstrates for this job
    target_skills = models.JSONField(
        default=list,
        help_text="Skills this experience was meant to demonstrate for this job"
    )
    
    # Match score when this link was created
    match_score = models.FloatField(
        null=True,
        blank=True,
        help_text="How well this experience matches job requirements (0-100)"
    )
    
    # When this link was established
    created_date = models.DateTimeField(auto_now_add=True)
    
    # Track creation source
    CREATION_SOURCE_CHOICES = [
        ('quick_add', 'Quick Add Modal'),
        ('manual_link', 'Manual User Link'),
        ('ai_suggestion', 'AI Suggested'),
        ('skill_gap_analysis', 'From Skill Gap Analysis'),
    ]
    creation_source = models.CharField(
        max_length=20,
        choices=CREATION_SOURCE_CHOICES,
        default='manual_link'
    )
    
    # User notes about why this experience is relevant
    relevance_notes = models.TextField(
        blank=True,
        help_text="User notes about how this experience relates to the job"
    )

    class Meta:
        db_table = 'job_experience'
        unique_together = ('job_posting', 'experience')  # Prevent duplicate links
        indexes = [
            models.Index(fields=['user', 'job_posting']),
            models.Index(fields=['user', 'relevance']),
            models.Index(fields=['job_posting', 'match_score']),
        ]

    def __str__(self):
        return f"{self.experience.title} → {self.job_posting.job_title}"

    @property
    def skill_match_count(self):
        """Count of target skills that this experience actually demonstrates"""
        if not self.target_skills:
            return 0
        experience_skills = [skill.lower() for skill in (self.experience.skills_used or [])]
        return len([skill for skill in self.target_skills if skill.lower() in experience_skills])

    def calculate_match_score(self):
        """Calculate how well this experience matches the job requirements"""
        if not self.target_skills:
            return 0.0
        
        skill_match_ratio = self.skill_match_count / len(self.target_skills)
        
        # Additional factors could include:
        # - Experience recency
        # - Experience type relevance
        # - Description keyword matches
        
        return round(skill_match_ratio * 100, 1)


class Note(models.Model):
    """Notes for job applications - interview notes, research, follow-up, etc."""

    CATEGORY_CHOICES = [
        ('interview_notes', 'Interview Notes'),
        ('interview_prep', 'Interview Prep'),
        ('research', 'Research'),
        ('follow_up', 'Follow-up'),
        ('other', 'Other'),
    ]

    note_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    body = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    job = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name='notes',
        null=True,
        blank=True,
        help_text="Job this note relates to. Can be null for general notes."
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_notes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'job']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['created_at']),
        ]
        db_table = 'job_note'

    def __str__(self):
        job_title = self.job.job_title if self.job else "General"
        return f"{self.title} - {job_title} ({self.get_category_display()})"


class NoteTemplate(models.Model):
    """Templates for creating notes - reusable note structures for common use cases"""

    CATEGORY_CHOICES = [
        ('interview_notes', 'Interview Notes'),
        ('interview_prep', 'Interview Prep'),
        ('research', 'Research'),
        ('follow_up', 'Follow-up'),
        ('other', 'Other'),
    ]

    template_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    body = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='note_templates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']  # Newest first
        indexes = [
            models.Index(fields=['user', 'category']),
            models.Index(fields=['created_at']),
        ]
        db_table = 'note_template'

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"