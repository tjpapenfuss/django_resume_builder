"""
Custom exceptions for the conversation system
"""


class ConversationError(Exception):
    """Base exception for conversation-related errors"""
    pass


class ConversationNotFoundError(ConversationError):
    """Raised when a conversation cannot be found"""
    pass


class ConversationStateError(ConversationError):
    """Raised when an operation is invalid for the current conversation state"""
    pass


class AIServiceError(ConversationError):
    """Raised when AI service encounters an error"""
    pass


class ConversationPermissionError(ConversationError):
    """Raised when user doesn't have permission to access a conversation"""
    pass