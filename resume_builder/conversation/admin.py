from django.contrib import admin
from .models import Conversation, ConversationMessage


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('conversation_id', 'user', 'status', 'message_count', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at', 'updated_at')
    search_fields = ('user__email', 'conversation_id')
    readonly_fields = ('conversation_id', 'created_at', 'updated_at', 'message_count')
    ordering = ('-updated_at',)
    
    fieldsets = (
        (None, {
            'fields': ('conversation_id', 'user', 'status')
        }),
        ('Summary', {
            'fields': ('experience_summary',),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'message_count'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):
    list_display = ('message_id', 'conversation', 'role', 'content_preview', 'timestamp')
    list_filter = ('role', 'timestamp')
    search_fields = ('conversation__user__email', 'content', 'message_id')
    readonly_fields = ('message_id', 'timestamp')
    ordering = ('-timestamp',)
    
    fieldsets = (
        (None, {
            'fields': ('message_id', 'conversation', 'role')
        }),
        ('Content', {
            'fields': ('content',),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('metadata', 'timestamp'),
            'classes': ('collapse',)
        }),
    )
    
    def content_preview(self, obj):
        """Show a preview of the message content in the admin list"""
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content Preview'