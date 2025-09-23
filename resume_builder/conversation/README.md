# Conversational Experience Extraction System

A Django-based AI-powered conversation system that helps users extract detailed work experiences through natural conversations. The system uses OpenAI/Anthropic APIs to conduct intelligent interviews and generate comprehensive experience summaries.

## Features

- **AI-Powered Conversations**: Natural language conversations guided by specialized prompts for experience extraction
- **Complete Conversation Lifecycle**: Start, pause, resume, and complete conversations with proper state management
- **Smart Completion Detection**: AI automatically detects when enough detail has been gathered
- **Comprehensive Summaries**: Generate structured summaries including resume bullets, interview stories, and skill identification
- **REST API**: Full REST API for integration with frontend applications
- **Real-time Testing Interface**: HTML interface for testing conversation flows

## API Endpoints

### Core Conversation Flow

- `POST /conversations/start/` - Start new conversation
- `POST /conversations/{id}/message/` - Send user message, get AI response
- `GET /conversations/{id}/history/` - Get conversation history
- `POST /conversations/{id}/complete/` - Complete conversation with summary
- `GET /conversations/{id}/status/` - Get conversation status
- `POST /conversations/{id}/pause/` - Pause/resume conversation
- `GET /conversations/` - List user's conversations

### Example API Usage

```python
# Start a conversation
response = requests.post('/conversations/start/', headers=auth_headers)
conversation_id = response.json()['conversation_id']

# Send a message
response = requests.post(f'/conversations/{conversation_id}/message/', 
    json={'content': 'I worked as a software engineer at TechCorp'},
    headers=auth_headers
)
ai_response = response.json()['ai_response']

# Complete the conversation
requests.post(f'/conversations/{conversation_id}/complete/', 
    json={'user_approved': True}, headers=auth_headers)
```

## AI System Prompt

The system uses a comprehensive prompt that instructs the AI to:

- Act as an expert career coach and experience extraction assistant
- Ask strategic follow-up questions about tools, technologies, impact, and challenges
- Adapt communication style based on user responses
- Recognize when sufficient detail has been gathered
- Generate structured summaries for resume and interview use

## Services Architecture

### ConversationManager (`services/conversation_manager.py`)
Core conversation lifecycle management:
- `start_conversation(user_id)` - Creates new conversation
- `add_message(conversation_id, role, content)` - Adds messages
- `get_conversation_history(conversation_id)` - Retrieves history
- `complete_conversation(conversation_id, summary)` - Completes with summary
- `pause_conversation(conversation_id)` - Pauses conversation

### AIService (`services/ai_service.py`)
AI integration and response generation:
- `generate_ai_response(messages)` - Gets AI responses from OpenAI/Anthropic
- `generate_experience_summary(conversation)` - Creates final structured summary
- `detect_conversation_completion(messages)` - Analyzes if conversation is ready to complete

### ConversationOrchestrator (`services/conversation_orchestrator.py`)
High-level orchestration combining conversation management with AI:
- `start_new_conversation(user_id)` - Full conversation startup with AI greeting
- `process_user_message(conversation_id, message)` - Complete message processing workflow
- `complete_conversation_with_summary(conversation_id)` - AI-powered completion

## Configuration

### Required Environment Variables

```bash
# At least one AI service required
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# Django settings
DJANGO_PROJECT_SECRET_KEY=your-secret-key
```

### Django Settings
The conversation app is automatically added to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ... other apps
    'conversation',
]
```

## Testing

### Basic System Test
```bash
# Test without AI (basic functionality)
python manage.py test_conversation_system --skip-ai

# Test with AI integration (requires API keys)
python manage.py test_conversation_system --user-email your@email.com
```

### Web Interface Test
Navigate to `/conversations/test/` for an interactive HTML interface to test the complete conversation flow.

## Database Models

### Conversation
- `conversation_id` (UUID, primary key)
- `user` (ForeignKey to User)
- `status` ('active', 'completed', 'paused')
- `experience_summary` (TextField, nullable)
- `created_at`, `updated_at` (timestamps)

### ConversationMessage
- `message_id` (UUID, primary key)
- `conversation` (ForeignKey to Conversation)
- `role` ('user', 'assistant')
- `content` (TextField)
- `metadata` (JSONField for AI metadata)
- `timestamp` (auto timestamp)

## Error Handling

The system includes comprehensive error handling:
- Custom exceptions for different error types
- Graceful API failure handling with fallbacks
- User-friendly error messages
- Proper HTTP status codes
- Logging for debugging

## Experience Summary Format

When conversations are completed, the AI generates structured summaries:

```json
{
  "narrative_summary": "Detailed paragraph describing the full experience",
  "resume_bullets": [
    "Impact-focused bullet point with quantifiable results",
    "Technology-focused bullet point with tools used"
  ],
  "interview_story": {
    "situation": "Context and challenge description",
    "action": "Specific actions taken",
    "result": "Measurable outcomes"
  },
  "skills_identified": {
    "technical_skills": ["Python", "Django", "AWS"],
    "soft_skills": ["Leadership", "Problem Solving"],
    "tools_technologies": ["Git", "Docker", "Kubernetes"]
  },
  "key_achievements": ["Specific measurable achievements"],
  "timeline": "Duration and timeframe",
  "role_context": "Job title and company context"
}
```

## Integration with Interview Assistant

The conversation system is designed to integrate with the existing interview assistant:
- Conversations are linked to user accounts
- Generated summaries can be used to create Experience objects
- Skills identified can be linked to the skills system
- Timeline information can populate employment records

## Future Enhancements

- Integration with existing Experience model creation
- Conversation templates for different experience types
- Multi-language support
- Voice conversation interface
- Analytics and conversation quality metrics
- Bulk experience extraction workflows