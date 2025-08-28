import openai
import json
from django.conf import settings
from django.utils import timezone
from skills.models import Skill, ExperienceSkill

def analyze_experience_with_ai(experience):
    """Analyze experience description with AI to extract skills"""
    
    # Skip if already analyzed recently (optional caching logic)
    if hasattr(experience, 'details') and experience.details.get('ai_analyzed_at'):
        return experience.details.get('ai_analysis', {})
    
    # Get the experience description
    description = experience.description
    title = experience.title
    
    if not description:
        return {}
    
    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        prompt = f"""
        Analyze this professional experience and extract skills in JSON format.
        Focus on technical skills, soft skills, tools, technologies, and methodologies.
        
        Experience Title: {title}
        Experience Description: {description}
        
        Return JSON in this exact format:
        {{
          "technical_skills": ["Python", "SQL", "Azure", "React"],
          "soft_skills": ["Leadership", "Communication", "Problem Solving"],
          "tools_and_technologies": ["Git", "Docker", "Jira", "Slack"],
          "methodologies": ["Agile", "Scrum", "DevOps"],
          "domain_expertise": ["Data Analysis", "Machine Learning", "Web Development"],
          "certifications_implied": ["AWS Certified", "PMP"],
          "confidence_scores": {{
            "technical_skills": 0.9,
            "soft_skills": 0.8,
            "tools_and_technologies": 0.85
          }},
          "skill_categories": {{
            "Programming": ["Python", "JavaScript"],
            "Cloud": ["Azure", "AWS"],
            "Communication": ["Presentation", "Writing"]
          }}
        }}
        
        Only include skills that are clearly evident from the description. Be specific and avoid generic terms.
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        response_content = response.choices[0].message.content
        if not response_content:
            return {}
        
        ai_analysis = json.loads(response_content)
        
        # Store analysis in experience details
        if not experience.details:
            experience.details = {}
        
        experience.details['ai_analysis'] = ai_analysis
        experience.details['ai_analyzed_at'] = timezone.now().isoformat()
        experience.save(update_fields=['details'])
        
        return ai_analysis
        
    except Exception as e:
        print(f"AI analysis failed for experience {experience.experience_id}: {str(e)}")
        return {}


def create_skills_from_analysis(user, ai_analysis, experience):
    """
    Create or link skills based on AI analysis results.
    Returns a dict with created_skills, existing_skills, and skill_links created.
    """
    print("Starting created skills")
    if not ai_analysis:
        return {
            'created_skills': [],
            'existing_skills': [],
            'skill_links': [],
            'errors': ['No AI analysis data provided']
        }
    
    created_skills = []
    existing_skills = []
    skill_links = []
    errors = []
    
    # Combine all skills from different categories
    all_skills = []
    skill_categories = ai_analysis.get('skill_categories', {})
    
    # Add skills from each category
    for category, skills in skill_categories.items():
        for skill_name in skills:
            all_skills.append({
                'name': skill_name.strip(),
                'category': category,
                'type': determine_skill_type(skill_name, category)
            })
    
    # Also add skills from direct lists (fallback)
    for skill_type in ['technical_skills', 'soft_skills', 'tools_and_technologies', 'methodologies', 'domain_expertise']:
        skills_list = ai_analysis.get(skill_type, [])
        for skill_name in skills_list:
            # Check if we already have this skill
            if not any(s['name'].lower() == skill_name.lower() for s in all_skills):
                all_skills.append({
                    'name': skill_name.strip(),
                    'category': map_skill_type_to_category(skill_type),
                    'type': map_skill_type(skill_type)
                })
    print(all_skills)
    # Process each skill
    for skill_data in all_skills:
        skill_name = skill_data['name']
        
        if len(skill_name) < 2:  # Skip very short skill names
            continue
            
        try:
            # Check if skill already exists for this user
            existing_skill = Skill.objects.filter(
                user=user, 
                title__iexact=skill_name
            ).first()
            
            if existing_skill:
                existing_skills.append(existing_skill)
                skill_obj = existing_skill
            else:
                # Create new skill
                skill_obj = Skill.objects.create(
                    user=user,
                    title=skill_name,
                    category=skill_data['category'],
                    skill_type=skill_data['type'],
                    description=f"Identified from experience: {experience.title}",
                    details={'extracted_from_ai': True, 'source_experience': str(experience.experience_id)}
                )
                created_skills.append(skill_obj)
            
            # Link skill to experience (avoid duplicates)
            experience_skill, created = ExperienceSkill.objects.get_or_create(
                experience=experience,
                skill=skill_obj,
                defaults={
                    'prominence': determine_prominence(skill_name, ai_analysis),
                    'extraction_method': 'ai_suggested',
                    'usage_notes': f'Extracted from AI analysis of: {experience.title}'
                }
            )
            
            if created:
                skill_links.append(experience_skill)
                
        except Exception as e:
            errors.append(f"Error processing skill '{skill_name}': {str(e)}")
    
    return {
        'created_skills': created_skills,
        'existing_skills': existing_skills, 
        'skill_links': skill_links,
        'errors': errors
    }


def determine_skill_type(skill_name, category):
    """Determine skill type based on skill name and category"""
    skill_name_lower = skill_name.lower()
    category_lower = category.lower()
    
    if category_lower in ['programming', 'technology', 'cloud', 'tools']:
        return 'Technical'
    elif category_lower in ['communication', 'leadership', 'management']:
        return 'Soft'
    elif skill_name_lower in ['python', 'java', 'sql', 'javascript', 'react', 'node.js']:
        return 'Technical'
    elif skill_name_lower in ['leadership', 'communication', 'teamwork', 'problem solving']:
        return 'Soft'
    else:
        return 'Hard'


def map_skill_type_to_category(skill_type):
    """Map AI analysis skill types to our category system"""
    mapping = {
        'technical_skills': 'Technology',
        'soft_skills': 'Communication',
        'tools_and_technologies': 'Technology', 
        'methodologies': 'Other',
        'domain_expertise': 'Other'
    }
    return mapping.get(skill_type, 'Other')


def map_skill_type(skill_type):
    """Map AI analysis skill types to our skill type choices"""
    mapping = {
        'technical_skills': 'Technical',
        'soft_skills': 'Soft',
        'tools_and_technologies': 'Technical',
        'methodologies': 'Hard',
        'domain_expertise': 'Hard'
    }
    return mapping.get(skill_type, 'Hard')


def determine_prominence(skill_name, ai_analysis):
    """Determine how prominent this skill was in the experience"""
    
    # Check confidence scores to determine prominence
    confidence_scores = ai_analysis.get('confidence_scores', {})
    
    technical_confidence = confidence_scores.get('technical_skills', 0.5)
    soft_confidence = confidence_scores.get('soft_skills', 0.5)
    
    # Check if skill appears in high-confidence categories
    technical_skills = ai_analysis.get('technical_skills', [])
    soft_skills = ai_analysis.get('soft_skills', [])
    
    if skill_name in technical_skills and technical_confidence > 0.8:
        return 'primary'
    elif skill_name in soft_skills and soft_confidence > 0.8:
        return 'primary'
    elif technical_confidence > 0.6 or soft_confidence > 0.6:
        return 'secondary'
    else:
        return 'supporting'