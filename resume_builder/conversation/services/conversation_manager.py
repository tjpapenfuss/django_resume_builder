"""
Conversation Management Service

Handles the core conversation lifecycle operations including creating,
managing, and completing conversations for experience extraction.
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from ..models import Conversation, ConversationMessage
from typing import Optional, Dict, List
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class ConversationManager:
    """Service class for managing conversation lifecycle operations"""
    
    @staticmethod
    def start_conversation(user_id: str) -> str:
        """
        Creates a new conversation for the specified user
        
        Args:
            user_id: UUID string of the user
            
        Returns:
            conversation_id: UUID string of the created conversation
            
        Raises:
            ValueError: If user doesn't exist
        """
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            raise ValueError(f"User with id {user_id} does not exist")
        
        conversation = Conversation.objects.create(
            user=user,
            status='active'
        )
        
        logger.info(f"Started conversation {conversation.conversation_id} for user {user.email}")
        return str(conversation.conversation_id)
    
    @staticmethod
    def add_message(conversation_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> str:
        """
        Adds a message to an existing conversation
        
        Args:
            conversation_id: UUID string of the conversation
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional additional context data
            
        Returns:
            message_id: UUID string of the created message
            
        Raises:
            ValueError: If conversation doesn't exist or is not active
        """
        try:
            conversation = Conversation.objects.get(conversation_id=conversation_id)
        except Conversation.DoesNotExist:
            raise ValueError(f"Conversation {conversation_id} does not exist")
        
        if conversation.status not in ['active', 'paused']:
            raise ValueError(f"Cannot add message to conversation with status: {conversation.status}")
        
        # If conversation was paused, reactivate it
        if conversation.status == 'paused':
            conversation.status = 'active'
            conversation.save(update_fields=['status', 'updated_at'])
        
        message = ConversationMessage.objects.create(
            conversation=conversation,
            role=role,
            content=content,
            metadata=metadata or {}
        )
        
        # Update conversation timestamp
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=['updated_at'])
        
        logger.info(f"Added {role} message to conversation {conversation_id}")
        return str(message.message_id)
    
    @staticmethod
    def get_conversation_history(conversation_id: str, include_metadata: bool = False) -> List[Dict]:
        """
        Retrieves formatted conversation history
        
        Args:
            conversation_id: UUID string of the conversation
            include_metadata: Whether to include message metadata
            
        Returns:
            List of message dictionaries with role, content, timestamp
            
        Raises:
            ValueError: If conversation doesn't exist
        """
        try:
            conversation = Conversation.objects.get(conversation_id=conversation_id)
        except Conversation.DoesNotExist:
            raise ValueError(f"Conversation {conversation_id} does not exist")
        
        messages = ConversationMessage.objects.filter(
            conversation=conversation
        ).order_by('timestamp')
        
        history = []
        for message in messages:
            message_data = {
                'message_id': str(message.message_id),
                'role': message.role,
                'content': message.content,
                'timestamp': message.timestamp.isoformat()
            }
            
            if include_metadata and message.metadata:
                message_data['metadata'] = message.metadata
            
            history.append(message_data)
        
        return history
    
    @staticmethod
    def get_conversation_for_ai(conversation_id: str) -> List[Dict]:
        """
        Gets conversation history formatted for AI API calls
        
        Args:
            conversation_id: UUID string of the conversation
            
        Returns:
            List of messages in format: [{"role": "user/assistant", "content": "..."}]
        """
        history = ConversationManager.get_conversation_history(conversation_id)
        
        # Format for AI API (remove timestamps and metadata)
        ai_messages = []
        for message in history:
            ai_messages.append({
                'role': message['role'],
                'content': message['content']
            })
        
        return ai_messages
    
    @staticmethod
    def complete_conversation(conversation_id: str, experience_summary: str) -> bool:
        """
        Marks a conversation as completed with final experience summary
        
        Args:
            conversation_id: UUID string of the conversation
            experience_summary: Final extracted experience summary
            
        Returns:
            Success boolean
            
        Raises:
            ValueError: If conversation doesn't exist or is already completed
        """
        try:
            conversation = Conversation.objects.get(conversation_id=conversation_id)
        except Conversation.DoesNotExist:
            raise ValueError(f"Conversation {conversation_id} does not exist")
        
        if conversation.status == 'completed':
            raise ValueError("Conversation is already completed")
        
        conversation.mark_completed(summary=experience_summary)
        
        logger.info(f"Completed conversation {conversation_id}")
        return True
    
    @staticmethod
    def pause_conversation(conversation_id: str) -> bool:
        """
        Pauses an active conversation to be resumed later
        
        Args:
            conversation_id: UUID string of the conversation
            
        Returns:
            Success boolean
            
        Raises:
            ValueError: If conversation doesn't exist or cannot be paused
        """
        try:
            conversation = Conversation.objects.get(conversation_id=conversation_id)
        except Conversation.DoesNotExist:
            raise ValueError(f"Conversation {conversation_id} does not exist")
        
        if conversation.status != 'active':
            raise ValueError(f"Cannot pause conversation with status: {conversation.status}")
        
        conversation.status = 'paused'
        conversation.save(update_fields=['status', 'updated_at'])
        
        logger.info(f"Paused conversation {conversation_id}")
        return True
    
    @staticmethod
    def get_conversation_status(conversation_id: str) -> Dict:
        """
        Gets detailed status information about a conversation
        
        Args:
            conversation_id: UUID string of the conversation
            
        Returns:
            Dictionary with conversation details
            
        Raises:
            ValueError: If conversation doesn't exist
        """
        try:
            conversation = Conversation.objects.get(conversation_id=conversation_id)
        except Conversation.DoesNotExist:
            raise ValueError(f"Conversation {conversation_id} does not exist")
        
        return {
            'conversation_id': str(conversation.conversation_id),
            'user_email': conversation.user.email,
            'status': conversation.status,
            'title': conversation.title,
            'message_count': conversation.message_count,
            'created_at': conversation.created_at.isoformat(),
            'updated_at': conversation.updated_at.isoformat(),
            'has_summary': bool(conversation.experience_summary),
            'last_message_time': conversation.last_message.timestamp.isoformat() if conversation.last_message else None
        }
    
    @staticmethod
    def get_user_conversations(user_id: str, status: Optional[str] = None) -> List[Dict]:
        """
        Gets all conversations for a user, optionally filtered by status
        
        Args:
            user_id: UUID string of the user
            status: Optional status filter ('active', 'completed', 'paused')
            
        Returns:
            List of conversation summary dictionaries
        """
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            raise ValueError(f"User with id {user_id} does not exist")
        
        conversations = Conversation.objects.filter(user=user)
        
        if status:
            conversations = conversations.filter(status=status)
        
        conversation_list = []
        for conv in conversations:
            conversation_list.append({
                'conversation_id': str(conv.conversation_id),
                'status': conv.status,
                'message_count': conv.message_count,
                'created_at': conv.created_at.isoformat(),
                'updated_at': conv.updated_at.isoformat(),
                'has_summary': bool(conv.experience_summary)
            })
        
        return conversation_list