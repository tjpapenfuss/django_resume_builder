"""
Django views for conversation API endpoints
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.urls import reverse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import json
import logging

from .services.conversation_orchestrator import conversation_orchestrator
from .serializers import (
    StartConversationSerializer,
    SendMessageSerializer,
    ConversationActionSerializer,
    ConversationStatusSerializer
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_conversation(request):
    """
    Start a new conversation for the authenticated user
    
    POST /conversations/start/
    """
    try:
        user_id = str(request.user.user_id)
        result = conversation_orchestrator.start_new_conversation(user_id)
        
        if result['success']:
            return Response({
                'success': True,
                'conversation_id': result['conversation_id'],
                'initial_message': result['initial_message'],
                'status': result['status']
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error starting conversation: {e}")
        return Response({
            'success': False,
            'error': 'Failed to start conversation'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request, conversation_id):
    """
    Send a user message and get AI response
    
    POST /conversations/{conversation_id}/message/
    """
    try:
        serializer = SendMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user_message = serializer.validated_data['content']
        
        # Verify conversation belongs to user
        conversation_status = conversation_orchestrator.conversation_manager.get_conversation_status(conversation_id)
        if conversation_status and request.user.email != conversation_status.get('user_email'):
            return Response({
                'success': False,
                'error': 'Access denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        result = conversation_orchestrator.process_user_message(conversation_id, user_message)
        
        if result['success']:
            response_data = {
                'success': True,
                'ai_response': result['ai_response'],
                'conversation_status': result['conversation_status'],
                'message_ids': {
                    'user_message': result['user_message_id'],
                    'ai_message': result['ai_message_id']
                }
            }
            
            # Include completion suggestion if available
            if result.get('suggested_completion'):
                response_data['completion_suggestion'] = {
                    'suggested': result['suggested_completion'],
                    'reason': result['completion_reason'],
                    'summary_preview': result.get('suggested_summary', {})
                }
            
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except ValueError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return Response({
            'success': False,
            'error': 'Failed to process message'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversation_history(request, conversation_id):
    """
    Get conversation history and status
    
    GET /conversations/{conversation_id}/history/
    """
    try:
        # Verify conversation belongs to user
        conversation_status = conversation_orchestrator.conversation_manager.get_conversation_status(conversation_id)
        if conversation_status and request.user.email != conversation_status.get('user_email'):
            return Response({
                'success': False,
                'error': 'Access denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        result = conversation_orchestrator.get_conversation_summary(conversation_id)
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        return Response({
            'success': False,
            'error': 'Failed to get conversation history'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_conversation(request, conversation_id):
    """
    Complete a conversation with final summary
    
    POST /conversations/{conversation_id}/complete/
    """
    try:
        # Verify conversation belongs to user
        conversation_status = conversation_orchestrator.conversation_manager.get_conversation_status(conversation_id)
        if conversation_status and request.user.email != conversation_status.get('user_email'):
            return Response({
                'success': False,
                'error': 'Access denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        user_approved = request.data.get('user_approved', True)
        result = conversation_orchestrator.complete_conversation_with_summary(
            conversation_id, user_approved
        )
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error completing conversation: {e}")
        return Response({
            'success': False,
            'error': 'Failed to complete conversation'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversation_status(request, conversation_id):
    """
    Get conversation status information
    
    GET /conversations/{conversation_id}/status/
    """
    try:
        # Verify conversation belongs to user
        conversation_status = conversation_orchestrator.conversation_manager.get_conversation_status(conversation_id)
        if conversation_status and request.user.email != conversation_status.get('user_email'):
            return Response({
                'success': False,
                'error': 'Access denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        return Response({
            'success': True,
            'conversation': conversation_status
        }, status=status.HTTP_200_OK)
            
    except ValueError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error getting conversation status: {e}")
        return Response({
            'success': False,
            'error': 'Failed to get conversation status'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pause_conversation(request, conversation_id):
    """
    Pause or resume a conversation
    
    POST /conversations/{conversation_id}/pause/
    """
    try:
        # Verify conversation belongs to user
        conversation_status = conversation_orchestrator.conversation_manager.get_conversation_status(conversation_id)
        if conversation_status and request.user.email != conversation_status.get('user_email'):
            return Response({
                'success': False,
                'error': 'Access denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        action = request.data.get('action', 'pause')
        result = conversation_orchestrator.pause_and_resume_conversation(conversation_id, action)
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error pausing/resuming conversation: {e}")
        return Response({
            'success': False,
            'error': 'Failed to modify conversation status'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_user_conversations(request):
    """
    Get all conversations for the authenticated user
    
    GET /conversations/
    """
    try:
        user_id = str(request.user.user_id)
        result = conversation_orchestrator.get_user_conversation_list(user_id)
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error listing user conversations: {e}")
        return Response({
            'success': False,
            'error': 'Failed to get user conversations'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Simple HTML view for testing
@login_required
def conversation_test_page(request):
    """Simple HTML page for testing the conversation system"""
    return render(request, 'conversation/test_conversation.html', {
        'user': request.user
    })


@login_required
def experience_assistant_page(request):
    """Enhanced experience assistant page with improved styling"""
    return render(request, 'conversation/experience_assistant.html', {
        'user': request.user
    })


@login_required
def create_experience_from_conversation(request, conversation_id):
    """
    Redirect to add experience page with conversation ID

    GET /conversations/{conversation_id}/create-experience/
    """
    try:
        # Verify conversation belongs to user
        from .models import Conversation
        conversation = Conversation.objects.get(
            conversation_id=conversation_id,
            user=request.user
        )

        # Redirect to add experience page with conversation_id parameter
        add_experience_url = reverse('experience:add_experience')
        return redirect(f"{add_experience_url}?conversation_id={conversation_id}")

    except Conversation.DoesNotExist:
        messages.error(request, 'Conversation not found or access denied.')
        return redirect('conversation:list_conversations')