from rest_framework import serializers
from .models import JobPosting, JobApplication, Note, NoteTemplate


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


class NoteTemplateSerializer(serializers.ModelSerializer):
    """Serializer for NoteTemplate model"""

    class Meta:
        model = NoteTemplate
        fields = [
            'template_id',
            'title',
            'body',
            'category',
            'user',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['template_id', 'user', 'created_at', 'updated_at']

    def validate_title(self, value):
        """Validate title is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Template title cannot be empty.")
        return value.strip()

    def validate_body(self, value):
        """Validate body is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Template body cannot be empty.")
        return value.strip()


class NoteTemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating note templates"""

    class Meta:
        model = NoteTemplate
        fields = ['title', 'body', 'category']

    def validate_title(self, value):
        """Validate title is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Template title cannot be empty.")
        return value.strip()

    def validate_body(self, value):
        """Validate body is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Template body cannot be empty.")
        return value.strip()