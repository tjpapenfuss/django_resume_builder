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