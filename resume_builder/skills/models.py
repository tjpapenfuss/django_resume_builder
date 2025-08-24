from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db.models import Q
from django.core.exceptions import ValidationError

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
        """
        Django-level validation (runs before saving via full_clean()).
        This ensures invalid data never even hits the database.
        """
        super().clean()
        
        # Only check for duplicate titles if both title and user are set
        if self.title and hasattr(self, 'user') and self.user:
            existing = Skill.objects.filter(
                user=self.user, 
                title=self.title
            ).exclude(skill_id=self.skill_id)
            if existing.exists():
                raise ValidationError({'title': 'You already have a skill with this title.'})  # Remove the backslash here

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