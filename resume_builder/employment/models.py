from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import uuid

class Employment(models.Model):
    employment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employments")
    company_name = models.CharField(max_length=255, null=False)
    location = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    details = models.JSONField(default=dict, blank=True, null=True)
    date_started = models.DateTimeField(null=True)
    date_finished = models.DateTimeField(null=True)
    created_date = models.DateTimeField(default=timezone.now, null=False)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'employment'  

    def __str__(self):
        return str(self.employment_id)