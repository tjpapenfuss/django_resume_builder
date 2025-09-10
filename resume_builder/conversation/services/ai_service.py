"""
AI Integration Service for Experience Extraction

Handles communication with AI APIs (OpenAI/Anthropic) to facilitate 
natural conversations for extracting detailed work experience information.
"""

import openai
import anthropic
from django.conf import settings
from typing import List, Dict, Optional, Tuple
import json
import logging

logger = logging.getLogger(__name__)


class AIService:
    """Service class for AI-powered conversation management"""
    
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        
        # Initialize available AI clients
        if settings.OPENAI_API_KEY:
            self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        if settings.ANTHROPIC_API_KEY:
            self.anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    def get_system_prompt(self) -> str:
        """
        Returns the comprehensive system prompt for experience extraction
        """
        return """You are an expert career coach and experience extraction assistant. Your role is to help users articulate their professional experiences in rich, detailed ways that will be valuable for resumes and interview preparation.

## Your Objectives:
1. **Extract Comprehensive Experience Details**: Guide users to describe their work experiences with specific details about responsibilities, tools, technologies, outcomes, and impact.

2. **Ask Strategic Follow-up Questions**: Based on user responses, ask clarifying questions about:
   - Specific tools, technologies, and methodologies used
   - Quantifiable outcomes and business impact
   - Team dynamics and collaboration aspects
   - Challenges faced and how they were overcome
   - Skills developed and demonstrated
   - Timeline and scope of responsibilities

3. **Adapt Communication Style**: 
   - For users who provide brief answers: Ask more guided, specific questions
   - For users who are naturally detailed: Ask broader questions and let them elaborate
   - Always be encouraging and professional

4. **Recognize Completion**: Know when you have gathered sufficient detail including:
   - Clear understanding of the role and responsibilities
   - Specific technologies, tools, and methods used
   - Quantifiable outcomes or impacts when possible
   - Timeline and context
   - Key challenges and achievements

5. **Generate Final Summary**: When the conversation is complete, provide:
   - **Narrative Summary**: A comprehensive paragraph describing the experience
   - **Resume Bullets**: 3-5 concise, impact-focused bullet points suitable for a resume
   - **Interview Story**: A structured story with situation, action, and result
   - **Skills Identified**: List of technical and soft skills demonstrated

## Conversation Guidelines:
- Start by understanding what experience the user wants to discuss
- Ask one focused question at a time
- Build on previous answers to go deeper
- Use encouraging language and show interest
- Maintain professional but friendly tone
- Summarize key points periodically to confirm understanding

## When to Conclude:
Signal completion when you have enough detail to create a comprehensive summary. Ask: "I think I have a good understanding of your experience. Would you like me to create a detailed summary, or is there anything else important you'd like to add?"

## Response Format:
- Keep responses conversational and engaging
- Ask clear, specific questions
- Acknowledge and build on user's answers
- End with a single, focused follow-up question (unless concluding)

Remember: Your goal is to help users recognize and articulate the full value of their professional experiences."""

    def generate_ai_response(self, messages: List[Dict], use_anthropic: bool = True) -> Tuple[str, Optional[Dict]]:
        """
        Generates AI response using available API
        
        Args:
            messages: List of conversation messages in format [{"role": "user/assistant", "content": "..."}]
            use_anthropic: Whether to prefer Anthropic over OpenAI
            
        Returns:
            Tuple of (response_content, metadata)
            
        Raises:
            Exception: If no AI service is available or API call fails
        """
        # Add system prompt to messages
        system_prompt = self.get_system_prompt()
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        # Try Anthropic first if preferred and available
        if use_anthropic and self.anthropic_client:
            try:
                return self._get_anthropic_response(full_messages)
            except Exception as e:
                logger.warning(f"Anthropic API failed: {e}. Falling back to OpenAI.")
                if self.openai_client:
                    return self._get_openai_response(full_messages)
                raise
        
        # Try OpenAI
        elif self.openai_client:
            try:
                return self._get_openai_response(full_messages)
            except Exception as e:
                logger.warning(f"OpenAI API failed: {e}. Falling back to Anthropic.")
                if self.anthropic_client:
                    return self._get_anthropic_response(full_messages)
                raise
        
        else:
            raise Exception("No AI service configured. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY.")
    
    def _get_anthropic_response(self, messages: List[Dict]) -> Tuple[str, Dict]:
        """Get response from Anthropic Claude"""
        # Convert messages format for Anthropic
        system_message = None
        conversation_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                conversation_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        response = self.anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            system=system_message,
            messages=conversation_messages
        )
        
        content = response.content[0].text
        metadata = {
            "model": "claude-3-sonnet-20240229",
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        }
        
        logger.info(f"Generated Anthropic response with {response.usage.output_tokens} tokens")
        return content, metadata
    
    def _get_openai_response(self, messages: List[Dict]) -> Tuple[str, Dict]:
        """Get response from OpenAI GPT"""
        response = self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        metadata = {
            "model": "gpt-3.5-turbo",
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
        
        logger.info(f"Generated OpenAI response with {response.usage.completion_tokens} tokens")
        return content, metadata
    
    def generate_experience_summary(self, conversation_messages: List[Dict]) -> Dict:
        """
        Generates final comprehensive experience summary from conversation
        
        Args:
            conversation_messages: Full conversation history
            
        Returns:
            Dictionary with structured summary components
        """
        summary_prompt = """Based on our conversation, please provide a comprehensive summary of this professional experience in the following JSON format:

{
  "title": "Concise experience title (e.g., 'Software Engineer at TechCorp')",
  "narrative_summary": "A detailed paragraph describing the full experience",
  "resume_bullets": [
    "Bullet point 1 with specific impact/outcome",
    "Bullet point 2 with tools/technologies",
    "Bullet point 3 with quantifiable results"
  ],
  "interview_story": {
    "situation": "Context and challenge",
    "action": "What you specifically did",
    "result": "Outcome and impact"
  },
  "skills_identified": {
    "technical_skills": ["Python", "SQL", "AWS"],
    "soft_skills": ["Leadership", "Problem Solving"],
    "tools_technologies": ["Git", "Docker", "Jira"]
  },
  "key_achievements": ["Specific measurable achievements"],
  "timeline": "Duration and timeframe",
  "role_context": "Job title and company context"
}

Please ensure all content is specific, quantifiable where possible, and professionally formatted."""
        
        # Add summary prompt to conversation
        messages_for_summary = conversation_messages + [
            {"role": "user", "content": summary_prompt}
        ]
        
        try:
            response_content, metadata = self.generate_ai_response(messages_for_summary, use_anthropic=True)
            
            # Try to parse JSON response
            try:
                summary_data = json.loads(response_content)
                summary_data['generation_metadata'] = metadata
                return summary_data
            except json.JSONDecodeError:
                # If JSON parsing fails, return raw response
                logger.warning("Failed to parse JSON summary, returning raw response")
                return {
                    "raw_summary": response_content,
                    "generation_metadata": metadata,
                    "parsing_error": "Failed to parse JSON response"
                }
                
        except Exception as e:
            logger.error(f"Failed to generate experience summary: {e}")
            return {
                "error": str(e),
                "fallback_summary": "Failed to generate AI summary. Please review conversation manually."
            }
    
    def generate_conversation_title(self, conversation_messages: List[Dict]) -> str:
        """
        Generates a concise title for the conversation based on the first user message
        
        Args:
            conversation_messages: Current conversation history
            
        Returns:
            String title for the conversation
        """
        title_prompt = """Based on this conversation about a professional experience, create a concise, descriptive title (max 50 characters) that captures the main topic.

Examples:
- "Software Engineer at TechCorp"
- "Project Manager - Mobile App Launch"
- "Data Analysis Internship"
- "Marketing Campaign Lead Role"

Make it clear and professional, focusing on the role or main responsibility discussed.

Respond with just the title, no additional text."""

        messages_for_title = conversation_messages + [
            {"role": "user", "content": title_prompt}
        ]
        
        try:
            response_content, _ = self.generate_ai_response(messages_for_title, use_anthropic=True)
            # Clean up the response - remove quotes and extra whitespace
            title = response_content.strip().strip('"\'').strip()
            
            # Ensure title is not too long
            if len(title) > 50:
                title = title[:47] + "..."
                
            return title
            
        except Exception as e:
            logger.warning(f"Failed to generate conversation title: {e}")
            # Fallback title
            return "Professional Experience Discussion"

    def detect_conversation_completion(self, conversation_messages: List[Dict]) -> Tuple[bool, str]:
        """
        Analyzes conversation to determine if enough detail has been gathered
        
        Args:
            conversation_messages: Current conversation history
            
        Returns:
            Tuple of (should_complete, reasoning)
        """
        completion_prompt = """Analyze this conversation about a professional experience. Determine if we have gathered enough detail to create a comprehensive summary suitable for resume and interview purposes.

Consider whether we have sufficient information about:
- Specific role and responsibilities
- Tools, technologies, and methodologies used
- Quantifiable outcomes or business impact
- Timeline and scope
- Key challenges and achievements

Respond in JSON format:
{
  "should_complete": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of why conversation should/shouldn't be completed",
  "missing_elements": ["list of key information still needed"]
}"""

        messages_for_analysis = conversation_messages + [
            {"role": "user", "content": completion_prompt}
        ]
        
        try:
            response_content, _ = self.generate_ai_response(messages_for_analysis, use_anthropic=True)
            analysis = json.loads(response_content)
            
            return analysis.get('should_complete', False), analysis.get('reasoning', 'Analysis unclear')
            
        except Exception as e:
            logger.warning(f"Failed to analyze conversation completion: {e}")
            # Conservative default - don't auto-complete if analysis fails
            return False, "Unable to analyze conversation completion"


# Global AI service instance
ai_service = AIService()