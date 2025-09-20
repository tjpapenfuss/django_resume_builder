from django.db import models
import uuid
from django.conf import settings


class Conversation(models.Model):
    """
    Represents a conversational session between user and AI for experience extraction.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('resumable', 'Resumable'),
    ]
    
    conversation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    title = models.CharField(max_length=200, blank=True, null=True, help_text="Auto-generated title based on conversation content")
    experience_summary = models.TextField(blank=True, null=True, help_text="Summary of extracted experience information")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'created_at']),
        ]
        db_table = 'conversation'
    
    def __str__(self):
        return f"Conversation {str(self.conversation_id)[:8]} - {self.user.email} ({self.status})"
    
    @property
    def message_count(self):
        """Returns the total number of messages in this conversation"""
        return self.messages.count()
    
    @property
    def last_message(self):
        """Returns the most recent message in this conversation"""
        return self.messages.order_by('-timestamp').first()
    
    def mark_completed(self, summary=None):
        """Mark conversation as completed with optional summary"""
        self.status = 'completed'
        if summary:
            self.experience_summary = summary
        self.save(update_fields=['status', 'experience_summary', 'updated_at'])

    def mark_resumable(self, summary=None):
        """Mark conversation as resumable (created experience but can continue)"""
        self.status = 'resumable'
        if summary:
            self.experience_summary = summary
        self.save(update_fields=['status', 'experience_summary', 'updated_at'])

    def resume_conversation(self):
        """Resume a conversation (regardless of current status)"""
        # Allow resuming from any status
        self.status = 'active'
        self.save(update_fields=['status', 'updated_at'])
        return True

    @property
    def is_resumable(self):
        """Returns True if conversation can be resumed"""
        return self.status == 'resumable'

    @property
    def created_experience(self):
        """Get the experience created from this conversation (if any)"""
        return self.experiences.first() if hasattr(self, 'experiences') else None


class ConversationMessage(models.Model):
    """
    Individual messages within a conversation session.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    
    message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField(help_text="Message content")
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional context or metadata")
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['conversation', 'timestamp']),
            models.Index(fields=['conversation', 'role']),
        ]
        db_table = 'conversation_message'
    
    def __str__(self):
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"{self.role}: {content_preview}"
    
    @property
    def is_user_message(self):
        """Returns True if this message is from the user"""
        return self.role == 'user'
    
    @property
    def is_assistant_message(self):
        """Returns True if this message is from the assistant"""
        return self.role == 'assistant'