from rest_framework import serializers
from .models import JobPosting, JobApplication, Note


class NoteSerializer(serializers.ModelSerializer):
    """Serializer for Note model"""

    class Meta:
        model = Note
        fields = [
            'note_id',
            'title',
            'body',
            'category',
            'job',
            'user',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['note_id', 'user', 'created_at', 'updated_at']

    def validate_title(self, value):
        """Validate title is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value.strip()

    def validate_body(self, value):
        """Validate body is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Note body cannot be empty.")
        return value.strip()


class NoteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating notes via job-specific endpoint"""

    class Meta:
        model = Note
        fields = ['title', 'body', 'category']

    def validate_title(self, value):
        """Validate title is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value.strip()

    def validate_body(self, value):
        """Validate body is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Note body cannot be empty.")
        return value.strip()