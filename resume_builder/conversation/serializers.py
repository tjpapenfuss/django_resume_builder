"""
Django REST Framework serializers for conversation API endpoints
"""

from rest_framework import serializers
from .models import Conversation, ConversationMessage


class ConversationMessageSerializer(serializers.ModelSerializer):
    """Serializer for conversation messages"""
    
    class Meta:
        model = ConversationMessage
        fields = [
            'message_id', 'role', 'content', 'metadata', 'timestamp'
        ]
        read_only_fields = ['message_id', 'timestamp']


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for conversations"""
    
    message_count = serializers.ReadOnlyField()
    messages = ConversationMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Conversation
        fields = [
            'conversation_id', 'status', 'experience_summary',
            'created_at', 'updated_at', 'message_count', 'messages'
        ]
        read_only_fields = ['conversation_id', 'created_at', 'updated_at', 'message_count']


class StartConversationSerializer(serializers.Serializer):
    """Serializer for starting a new conversation"""
    pass  # No input required, user is taken from request


class SendMessageSerializer(serializers.Serializer):
    """Serializer for sending a message in a conversation"""
    
    content = serializers.CharField(max_length=10000, help_text="Message content")
    
    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Message content cannot be empty")
        return value.strip()


class ConversationActionSerializer(serializers.Serializer):
    """Serializer for conversation actions (pause, complete, etc.)"""
    
    action = serializers.ChoiceField(
        choices=['pause', 'resume', 'complete'],
        help_text="Action to perform on the conversation"
    )
    user_approved = serializers.BooleanField(
        default=True,
        help_text="User approval for completion (required for complete action)"
    )


class ConversationStatusSerializer(serializers.Serializer):
    """Serializer for conversation status response"""
    
    conversation_id = serializers.UUIDField()
    user_email = serializers.EmailField()
    status = serializers.CharField()
    message_count = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    has_summary = serializers.BooleanField()
    last_message_time = serializers.DateTimeField(allow_null=True)