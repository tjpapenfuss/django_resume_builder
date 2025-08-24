from django.db import models
import uuid
from django.conf import settings

class Experience(models.Model):
    # Define the types of experiences a user can add
    EXPERIENCE_TYPES = [
        ('project', 'Project'),
        ('achievement', 'Achievement'),
        ('responsibility', 'Responsibility'),
        ('certification', 'Certification'),
        ('award', 'Award'),
        ('presentation', 'Presentation'),
        ('publication', 'Publication'),
        ('volunteer', 'Volunteer Work'),
        ('other', 'Other'),
    ]
    
    # Control who can see the experience (resume, private, draft)
    VISIBILITY_CHOICES = [
        ('public', 'Include in Resumes'),
        ('private', 'Personal Reference Only'),
        ('draft', 'Draft - Not Ready'),
    ]
    
    # Primary key (UUID ensures global uniqueness instead of auto-increment ID)
    experience_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link experience to the user who owns it
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='experiences')
    
    # Core experience info
    title = models.CharField(max_length=200)  # e.g. "Software Engineer", "Won Hackathon"
    description = models.TextField(help_text="Detailed description of the experience")
    experience_type = models.CharField(max_length=20, choices=EXPERIENCE_TYPES, default='project')
    
    # Optional links to employment or education records
    employment = models.ForeignKey("employment.Employment", on_delete=models.CASCADE, related_name="experiences")
    education = models.ForeignKey("education.Education", on_delete=models.CASCADE, related_name="experiences")

    # Timeframe of the experience
    date_started = models.DateField(null=True, blank=True)
    date_finished = models.DateField(null=True, blank=True)
    
    # Skills and tags (flexible JSON fields instead of rigid tables)
    skills_used = models.JSONField(default=list, blank=True, help_text="List of skills/technologies used")
    tags = models.JSONField(default=list, blank=True, help_text="Tags for categorizing and filtering")
    
    # Flexible extra details (stored as JSON key/value pairs)
    details = models.JSONField(default=dict, blank=True)
    
    # Metadata about the experience
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public')
    created_date = models.DateTimeField(auto_now_add=True)  # Set once when created
    modified_date = models.DateTimeField(auto_now=True)     # Updates every save
    
    class Meta:
        # Default ordering: newest first by start date, then creation date
        ordering = ['-date_started', '-created_date']
        # Indexes speed up queries for filtering and lookups
        indexes = [
            models.Index(fields=['user', 'visibility']),
            models.Index(fields=['user', 'experience_type']),
            models.Index(fields=['employment']),
            models.Index(fields=['education']),
        ]
        db_table = "experience"   

    def __str__(self):
        """
        String representation of the experience.
        Example: "Software Engineer at Google" or "Research Assistant at MIT"
        """
        context = ""
        if self.employment:
            context = f" at {self.employment.company_name}"
        elif self.education:
            context = f" at {self.education.institution_name}"
        return f"{self.title}{context}"
    
    @property
    def duration_text(self):
        """
        Returns a human-readable duration string.
        Example: "Jan 2020 - Dec 2021" or "Feb 2022 - Present"
        """
        if not self.date_started:
            return "Date not specified"
        
        start = self.date_started.strftime("%b %Y")
        if self.date_finished:
            end = self.date_finished.strftime("%b %Y")
            return f"{start} - {end}"
        else:
            return f"{start} - Present"
    
    @property
    def context_name(self):
        """
        Returns the company/institution name if linked.
        Otherwise, returns 'Standalone Experience'.
        """
        if self.employment:
            return self.employment.company_name
        elif self.education:
            return self.education.institution_name
        return "Standalone Experience"
    
    @property
    def is_current(self):
        """
        Returns True if the experience has started but not finished.
        """
        return self.date_started and not self.date_finished
    
    def get_tags_for_job_type(self, job_type_tags):
        """
        Returns the number of overlapping tags between this experience
        and a given set of job_type_tags.
        Used to calculate relevance for resumes.
        """
        if not self.tags or not job_type_tags:
            return 0
        return len(set(self.tags) & set(job_type_tags))
    
    @classmethod
    def get_experiences_for_resume(cls, user, job_type_tags=None, limit=None):
        """
        Get experiences for a user's resume.
        - Only includes 'public' experiences.
        - If job_type_tags are given, rank by tag relevance first, then by date.
        - Can optionally limit the number of results.
        """
        experiences = cls.objects.filter(
            user=user,
            visibility='public'
        )
        
        if job_type_tags:
            relevant_experiences = []
            for exp in experiences:
                relevance_score = exp.get_tags_for_job_type(job_type_tags)
                if relevance_score > 0:
                    relevant_experiences.append((exp, relevance_score))
            
            # Sort by: highest relevance first, then latest date
            relevant_experiences.sort(
                key=lambda x: (-x[1], x[0].date_started or x[0].created_date.date()),
                reverse=True
            )
            experiences = [exp[0] for exp in relevant_experiences]
        
        if limit:
            return experiences[:limit]
        
        return experiences
