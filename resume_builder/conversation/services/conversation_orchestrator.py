"""
Conversation Orchestrator

Main service that orchestrates the full conversation flow, combining
conversation management with AI services for seamless user experience.
"""

from .conversation_manager import ConversationManager
from .ai_service import ai_service
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ConversationOrchestrator:
    """
    High-level service that orchestrates the complete conversation experience
    by combining conversation management with AI services
    """
    
    def __init__(self):
        self.conversation_manager = ConversationManager()
        self.ai_service = ai_service
    
    def start_new_conversation(self, user_id: str) -> Dict:
        """
        Starts a new conversation and provides initial AI greeting
        
        Args:
            user_id: UUID string of the user
            
        Returns:
            Dictionary with conversation_id and initial AI message
        """
        try:
            # Create new conversation
            conversation_id = self.conversation_manager.start_conversation(user_id)
            
            # Generate initial AI greeting
            initial_messages = []
            ai_response, ai_metadata = self.ai_service.generate_ai_response(initial_messages)
            
            # Add AI greeting to conversation
            self.conversation_manager.add_message(
                conversation_id, 
                'assistant', 
                ai_response,
                ai_metadata
            )
            
            return {
                'success': True,
                'conversation_id': conversation_id,
                'initial_message': ai_response,
                'status': 'active'
            }
            
        except Exception as e:
            logger.error(f"Failed to start conversation for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_user_message(self, conversation_id: str, user_message: str) -> Dict:
        """
        Processes user message and generates AI response
        
        Args:
            conversation_id: UUID string of the conversation
            user_message: User's message content
            
        Returns:
            Dictionary with AI response and conversation status
        """
        try:
            # Add user message to conversation
            user_message_id = self.conversation_manager.add_message(
                conversation_id, 
                'user', 
                user_message
            )
            
            # Get conversation history for AI
            conversation_history = self.conversation_manager.get_conversation_for_ai(conversation_id)
            
            # Generate AI response
            ai_response, ai_metadata = self.ai_service.generate_ai_response(conversation_history)
            
            # Add AI response to conversation
            ai_message_id = self.conversation_manager.add_message(
                conversation_id, 
                'assistant', 
                ai_response,
                ai_metadata
            )
            
            # Generate title after first user message (only if conversation doesn't have a title yet)
            conversation_status = self.conversation_manager.get_conversation_status(conversation_id)
            if not conversation_status.get('title'):
                try:
                    title = self.ai_service.generate_conversation_title(conversation_history)
                    # Update conversation with title
                    from ..models import Conversation
                    conversation = Conversation.objects.get(conversation_id=conversation_id)
                    conversation.title = title
                    conversation.save(update_fields=['title', 'updated_at'])
                except Exception as e:
                    logger.warning(f"Failed to generate title for conversation {conversation_id}: {e}")
            
            # Check if conversation should be completed
            should_complete, completion_reason = self.ai_service.detect_conversation_completion(
                conversation_history + [{'role': 'assistant', 'content': ai_response}]
            )
            
            response_data = {
                'success': True,
                'ai_response': ai_response,
                'user_message_id': user_message_id,
                'ai_message_id': ai_message_id,
                'conversation_status': 'active',
                'suggested_completion': should_complete,
                'completion_reason': completion_reason
            }
            
            # If AI suggests completion, include summary
            if should_complete:
                summary_data = self.ai_service.generate_experience_summary(conversation_history)
                response_data['suggested_summary'] = summary_data
            
            return response_data
            
        except Exception as e:
            logger.error(f"Failed to process message in conversation {conversation_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'conversation_status': 'error'
            }
    
    def complete_conversation_with_summary(self, conversation_id: str, user_approved: bool = True, for_experience: bool = True) -> Dict:
        """
        Completes conversation with AI-generated summary

        Args:
            conversation_id: UUID string of the conversation
            user_approved: Whether user approved the completion
            for_experience: Whether this completion is for creating an experience (makes it resumable)

        Returns:
            Dictionary with completion status and final summary
        """
        try:
            if not user_approved:
                return {
                    'success': False,
                    'error': 'User did not approve conversation completion'
                }

            # Get conversation history
            conversation_history = self.conversation_manager.get_conversation_for_ai(conversation_id)

            # Generate comprehensive summary
            experience_summary = self.ai_service.generate_experience_summary(conversation_history)

            # Complete conversation with summary
            summary_text = experience_summary.get('narrative_summary',
                                                str(experience_summary))

            # Check if this conversation already has an experience (resumed conversation)
            from ..models import Conversation
            conversation = Conversation.objects.get(conversation_id=conversation_id)
            existing_experience = conversation.experiences.first()

            if for_experience:
                if existing_experience:
                    # This is a resumed conversation with existing experience
                    # Mark as resumable again and update experience summary
                    self.conversation_manager.complete_conversation_with_experience(conversation_id, summary_text)
                    conversation_status = 'resumable'
                    message = 'Experience updated with additional context - you can continue adding more details anytime'
                else:
                    # First time creating experience
                    self.conversation_manager.complete_conversation_with_experience(conversation_id, summary_text)
                    conversation_status = 'resumable'
                    message = 'Conversation ready for experience creation - you can resume anytime to add more context'
            else:
                # Traditional completion
                self.conversation_manager.complete_conversation(conversation_id, summary_text)
                conversation_status = 'completed'
                message = 'Conversation completed successfully'

            return {
                'success': True,
                'conversation_status': conversation_status,
                'experience_summary': experience_summary,
                'message': message
            }
            
        except Exception as e:
            logger.error(f"Failed to complete conversation {conversation_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_conversation_summary(self, conversation_id: str) -> Dict:
        """
        Gets comprehensive conversation information including AI analysis
        
        Args:
            conversation_id: UUID string of the conversation
            
        Returns:
            Dictionary with conversation details and summary
        """
        try:
            # Get conversation status
            conversation_status = self.conversation_manager.get_conversation_status(conversation_id)
            
            # Get conversation history
            conversation_history = self.conversation_manager.get_conversation_history(
                conversation_id, include_metadata=True
            )
            
            response_data = {
                'success': True,
                'conversation': conversation_status,
                'message_history': conversation_history
            }
            
            # If conversation is completed, include the stored summary
            if conversation_status['status'] == 'completed' and conversation_status['has_summary']:
                from ..models import Conversation
                conversation = Conversation.objects.get(conversation_id=conversation_id)
                response_data['stored_summary'] = conversation.experience_summary
            
            # If conversation is active, check if it's ready for completion
            elif conversation_status['status'] == 'active':
                ai_messages = self.conversation_manager.get_conversation_for_ai(conversation_id)
                should_complete, reason = self.ai_service.detect_conversation_completion(ai_messages)
                response_data['completion_suggestion'] = {
                    'should_complete': should_complete,
                    'reason': reason
                }
            
            return response_data
            
        except Exception as e:
            logger.error(f"Failed to get conversation summary for {conversation_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def pause_and_resume_conversation(self, conversation_id: str, action: str) -> Dict:
        """
        Pauses or resumes a conversation
        
        Args:
            conversation_id: UUID string of the conversation
            action: 'pause' or 'resume'
            
        Returns:
            Dictionary with operation status
        """
        try:
            if action == 'pause':
                success = self.conversation_manager.pause_conversation(conversation_id)
                message = 'Conversation paused successfully'
            elif action == 'resume':
                # Resuming is handled automatically when adding a new message
                # Just verify conversation exists and is paused
                status = self.conversation_manager.get_conversation_status(conversation_id)
                if status['status'] != 'paused':
                    return {
                        'success': False,
                        'error': f"Cannot resume conversation with status: {status['status']}"
                    }
                success = True
                message = 'Conversation ready to resume'
            else:
                return {
                    'success': False,
                    'error': f"Invalid action: {action}. Must be 'pause' or 'resume'"
                }
            
            return {
                'success': success,
                'message': message,
                'conversation_status': action + 'd' if action == 'pause' else 'active'
            }
            
        except Exception as e:
            logger.error(f"Failed to {action} conversation {conversation_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_user_conversation_list(self, user_id: str) -> Dict:
        """
        Gets all conversations for a user with summary information
        
        Args:
            user_id: UUID string of the user
            
        Returns:
            Dictionary with user's conversations
        """
        try:
            conversations = self.conversation_manager.get_user_conversations(user_id)
            
            return {
                'success': True,
                'conversations': conversations,
                'total_count': len(conversations),
                'active_count': len([c for c in conversations if c['status'] == 'active']),
                'completed_count': len([c for c in conversations if c['status'] == 'completed'])
            }
            
        except Exception as e:
            logger.error(f"Failed to get conversations for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Global orchestrator instance
conversation_orchestrator = ConversationOrchestrator()