from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
#from datetime import datetime, timezone

from .managers import UserManager

class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.CharField(primary_key=True, max_length=40, editable=False)
    email = models.EmailField(max_length=100, unique=True)
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=80, blank=True, null=True)
    google_id = models.CharField(max_length=30, unique=True)
    login_count = models.IntegerField(default=1)
    last_login = models.DateTimeField(default=timezone.now, null=True)
    terms_and_conditions_accepted = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'user_id'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.user_id
    
class UserToken(models.Model):
    token = models.CharField(max_length=255, primary_key=True, unique=True)

    # Foreign Key to CustomUser model
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', related_name='user_token')

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self):
        # Check if the token is still valid based on expiration
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True