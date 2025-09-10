"""
Management command to test the conversation system
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from conversation.services.conversation_orchestrator import conversation_orchestrator
from conversation.services.ai_service import ai_service

User = get_user_model()


class Command(BaseCommand):
    help = 'Test the conversation system functionality'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user-email',
            type=str,
            help='Email of user to test with (will create if not exists)',
            default='test@example.com'
        )
        parser.add_argument(
            '--skip-ai',
            action='store_true',
            help='Skip AI integration test (useful if no API keys configured)'
        )
    
    def handle(self, *args, **options):
        user_email = options['user_email']
        skip_ai = options['skip_ai']
        
        self.stdout.write(f"Testing conversation system with user: {user_email}")
        
        # Get or create test user
        user, created = User.objects.get_or_create(
            email=user_email,
            defaults={
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        if created:
            self.stdout.write(f"Created test user: {user.email}")
        else:
            self.stdout.write(f"Using existing user: {user.email}")
        
        try:
            # Test 1: Start conversation
            self.stdout.write("🔄 Testing conversation start...")
            
            if not skip_ai:
                result = conversation_orchestrator.start_new_conversation(str(user.user_id))
                if result['success']:
                    conversation_id = result['conversation_id']
                    self.stdout.write(f"✅ Started conversation: {conversation_id}")
                    self.stdout.write(f"   Initial message: {result['initial_message'][:100]}...")
                else:
                    self.stdout.write(f"❌ Failed to start conversation: {result['error']}")
                    return
            else:
                # Skip AI for basic testing
                from conversation.services.conversation_manager import ConversationManager
                conversation_id = ConversationManager.start_conversation(str(user.user_id))
                self.stdout.write(f"✅ Started conversation (no AI): {conversation_id}")
            
            # Test 2: Get conversation status
            self.stdout.write("🔄 Testing conversation status...")
            status = conversation_orchestrator.conversation_manager.get_conversation_status(conversation_id)
            self.stdout.write(f"✅ Conversation status: {status['status']}")
            self.stdout.write(f"   Message count: {status['message_count']}")
            
            # Test 3: Add message
            self.stdout.write("🔄 Testing message addition...")
            if not skip_ai:
                result = conversation_orchestrator.process_user_message(
                    conversation_id, 
                    "I worked as a software engineer at TechCorp for 2 years, building web applications using Python and Django."
                )
                if result['success']:
                    self.stdout.write(f"✅ Processed user message")
                    self.stdout.write(f"   AI response: {result['ai_response'][:100]}...")
                else:
                    self.stdout.write(f"❌ Failed to process message: {result['error']}")
            else:
                # Manual message addition for basic testing
                from conversation.services.conversation_manager import ConversationManager
                ConversationManager.add_message(
                    conversation_id, 
                    'user', 
                    "Test message without AI"
                )
                self.stdout.write(f"✅ Added test message (no AI)")
            
            # Test 4: Get conversation history
            self.stdout.write("🔄 Testing conversation history retrieval...")
            history = conversation_orchestrator.conversation_manager.get_conversation_history(conversation_id)
            self.stdout.write(f"✅ Retrieved conversation history: {len(history)} messages")
            
            # Test 5: Pause conversation
            self.stdout.write("🔄 Testing conversation pause...")
            result = conversation_orchestrator.pause_and_resume_conversation(conversation_id, 'pause')
            if result['success']:
                self.stdout.write("✅ Successfully paused conversation")
            else:
                self.stdout.write(f"❌ Failed to pause conversation: {result['error']}")
            
            # Test 6: Complete conversation (if AI available)
            if not skip_ai:
                self.stdout.write("🔄 Testing conversation completion...")
                result = conversation_orchestrator.complete_conversation_with_summary(conversation_id, True)
                if result['success']:
                    self.stdout.write("✅ Successfully completed conversation")
                    if 'experience_summary' in result:
                        summary = result['experience_summary']
                        if 'narrative_summary' in summary:
                            self.stdout.write(f"   Summary: {summary['narrative_summary'][:100]}...")
                else:
                    self.stdout.write(f"❌ Failed to complete conversation: {result['error']}")
            
            # Test 7: List user conversations
            self.stdout.write("🔄 Testing user conversation listing...")
            result = conversation_orchestrator.get_user_conversation_list(str(user.user_id))
            if result['success']:
                self.stdout.write(f"✅ User has {result['total_count']} conversations")
                self.stdout.write(f"   Active: {result['active_count']}, Completed: {result['completed_count']}")
            else:
                self.stdout.write(f"❌ Failed to list conversations: {result['error']}")
            
            # Test AI service separately if available
            if not skip_ai:
                self.stdout.write("🔄 Testing AI service directly...")
                try:
                    system_prompt = ai_service.get_system_prompt()
                    self.stdout.write(f"✅ AI system prompt length: {len(system_prompt)} characters")
                    
                    # Test basic AI response
                    test_messages = [{"role": "user", "content": "Hello, I want to discuss my work experience."}]
                    response, metadata = ai_service.generate_ai_response(test_messages)
                    self.stdout.write(f"✅ AI response generated: {len(response)} characters")
                    self.stdout.write(f"   Model used: {metadata.get('model', 'unknown')}")
                except Exception as e:
                    self.stdout.write(f"❌ AI service test failed: {str(e)}")
            
            self.stdout.write("\n🎉 Conversation system test completed successfully!")
            
        except Exception as e:
            self.stdout.write(f"\n❌ Test failed with error: {str(e)}")
            raise