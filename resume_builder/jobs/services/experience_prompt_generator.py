# Create this file as jobs/services/experience_prompt_generator.py

import json
import requests
from django.conf import settings
from typing import Optional, Dict, Any


class ExperiencePromptGenerator:
    """
    Generates personalized experience prompts based on job descriptions and specific skills
    """
    
    def __init__(self, job_posting, skill_name: str):
        self.job = job_posting
        self.skill_name = skill_name
        self.job_description = self._extract_job_description()
        self.company_context = self._extract_company_context()
    
    def generate_prompt(self) -> Optional[str]:
        """
        Generate a personalized prompt using AI based on job description and skill
        """
        try:
            # Try different AI services in order of preference
            prompt = self._generate_with_openai()
            if prompt:
                return prompt
            
            # Fallback to other services if available
            # prompt = self._generate_with_anthropic()
            # if prompt:
            #     return prompt
            
            # If all AI services fail, return None (will use fallback)
            return None
            
        except Exception as e:
            print(f"Error generating AI prompt: {str(e)}")
            return None
    
    def _extract_job_description(self) -> str:
        """Extract relevant job description text"""
        try:
            # Get job description from various possible sources
            raw_json = getattr(self.job, 'raw_json', {})
            
            scraped_content = raw_json.get('scraped_content', {})
            
            # Try to get description from multiple sources
            description_parts = []
            
            if scraped_content.get('description'):
                description_parts.append(scraped_content['description'])
            
            if scraped_content.get('requirements'):
                description_parts.append(scraped_content['requirements'])
            
            if scraped_content.get('responsibilities'):
                description_parts.append(scraped_content['responsibilities'])
            
            # Fallback to basic job fields
            if not description_parts:
                if hasattr(self.job, 'description') and self.job.description:
                    description_parts.append(self.job.description)
                
                if hasattr(self.job, 'requirements') and self.job.requirements:
                    description_parts.append(str(self.job.requirements))
            
            return ' '.join(description_parts) if description_parts else ""
            
        except Exception as e:
            print(f"Error extracting job description: {str(e)}")
            return ""
    
    def _extract_company_context(self) -> Dict[str, Any]:
        """Extract company and role context"""
        return {
            'company_name': getattr(self.job, 'company_name', 'the company'),
            'job_title': getattr(self.job, 'job_title', 'this role'),
            'location': getattr(self.job, 'location', ''),
            'seniority': self._extract_seniority_level(),
            'industry': self._extract_industry_hints()
        }
    
    def _extract_seniority_level(self) -> str:
        """Extract seniority level from job title or description"""
        job_title = getattr(self.job, 'job_title', '').lower()
        job_desc = self.job_description.lower()
        
        if any(word in job_title for word in ['senior', 'lead', 'principal', 'staff']):
            return 'senior'
        elif any(word in job_title for word in ['junior', 'associate', 'entry']):
            return 'junior'
        elif any(word in job_title for word in ['manager', 'director', 'head']):
            return 'management'
        else:
            return 'mid-level'
    
    def _extract_industry_hints(self) -> str:
        """Extract industry context from company name or description"""
        company_name = getattr(self.job, 'company_name', '').lower()
        job_desc = self.job_description.lower()
        
        # Simple industry detection
        if any(word in company_name + ' ' + job_desc for word in ['tech', 'software', 'startup', 'saas']):
            return 'technology'
        elif any(word in company_name + ' ' + job_desc for word in ['bank', 'financial', 'finance']):
            return 'finance'
        elif any(word in company_name + ' ' + job_desc for word in ['health', 'medical', 'hospital']):
            return 'healthcare'
        else:
            return 'general'
    
    def _generate_with_openai(self) -> Optional[str]:
        """Generate prompt using OpenAI API"""
        try:
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if not api_key:
                return None
            
            system_prompt = self._create_system_prompt()
            user_prompt = self._create_user_prompt()
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'gpt-4',
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_prompt}
                    ],
                    'max_tokens': 800,
                    'temperature': 0.7
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content'].strip()
            
            return None
            
        except Exception as e:
            print(f"OpenAI API error: {str(e)}")
            return None
    
    def _generate_with_anthropic(self) -> Optional[str]:
        """Generate prompt using Anthropic Claude API"""
        try:
            api_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
            if not api_key:
                return None
            
            prompt = self._create_anthropic_prompt()
            
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'x-api-key': api_key,
                    'Content-Type': 'application/json',
                    'anthropic-version': '2023-06-01'
                },
                json={
                    'model': 'claude-3-sonnet-20240229',
                    'max_tokens': 800,
                    'messages': [{'role': 'user', 'content': prompt}]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['content'][0]['text'].strip()
            
            return None
            
        except Exception as e:
            print(f"Anthropic API error: {str(e)}")
            return None
    
    def _create_system_prompt(self) -> str:
        """Create system prompt for OpenAI"""
        return """
        You are an expert career coach and resume writer. Your task is to generate personalized experience prompts that help users articulate their professional experiences in a compelling way.

        Guidelines:
        1. Create specific, actionable prompts that help users think deeply about their experience
        2. Include context about the target job and company when relevant
        3. Use the STAR method (Situation, Task, Action, Result) framework
        4. Encourage specific details and quantifiable results
        5. Make the prompt engaging and motivating
        6. Keep the tone professional but encouraging
        7. Format the response in HTML for display in a web interface
        8. Focus on helping the user understand what specific aspects of their experience would be most relevant

        The prompt should help the user tell a compelling story that demonstrates the requested skill in a way that would appeal to the target employer.
        """
    
    def _create_user_prompt(self) -> str:
        """Create a concise user prompt with job and skill context"""
        return f"""
        Generate a brief, engaging 2-3 sentence prompt for a job applicant to help them think about their {self.skill_name} experience.

        Context:
        - Role: {self.company_context['job_title']} at {self.company_context['company_name']}
        - Skill: {self.skill_name}
        - Industry: {self.company_context['industry']}

        Job requirements excerpt: {self.job_description[:500]}

        Create 2-3 sentences that:
        1. Briefly acknowledge the role and company
        2. Ask them to think of a specific situation using {self.skill_name}
        3. Include 2-3 specific action examples relevant to this job (like "Did you design data models, create data flows, or leverage Snowflake's unique features?")

        Keep it conversational, encouraging, and focused. No STAR method explanation needed.
        Format as plain HTML paragraphs.
        """

    def _create_anthropic_prompt(self) -> str:
        """Create a concise prompt for Anthropic Claude"""
        return f"""
        Create a brief 2-3 sentence experience prompt for someone applying to a {self.company_context['job_title']} role at {self.company_context['company_name']}.

        They need to describe their experience with: {self.skill_name}

        Job context: {self.job_description[:500]}

        Generate 2-3 sentences that:
        - Acknowledge the specific role/company
        - Ask for a specific situation using {self.skill_name}  
        - Include 2-3 concrete action examples relevant to this job

        Be encouraging and specific. Return as HTML paragraphs only.
        """


# Helper function for settings configuration
def get_ai_service_config():
    """
    Return configuration for AI services
    Add this to your Django settings.py:
    
    # AI Service Configuration
    OPENAI_API_KEY = 'your-openai-api-key'  # Optional
    ANTHROPIC_API_KEY = 'your-anthropic-api-key'  # Optional
    
    # You can also use environment variables:
    import os
    
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    """
    OPENAI_API_KEY = settings.OPENAI_API_KEY
    return {
        'openai_available': bool(getattr(settings, 'OPENAI_API_KEY', None)),
        'anthropic_available': bool(getattr(settings, 'ANTHROPIC_API_KEY', None)),
    }