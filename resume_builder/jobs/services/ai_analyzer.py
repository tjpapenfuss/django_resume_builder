import openai
import json
from django.conf import settings
from django.utils import timezone

def analyze_job_with_ai(job_posting):
    """Analyze job posting with AI and cache the results"""
    
    # Skip if already analyzed recently (optional caching logic)
    if job_posting.has_ai_analysis:
        return job_posting.ai_analysis
    
    # Extract description from raw_json
    description = job_posting.raw_json.get('scraped_content', {}).get('full_description', '')
    
    if not description:
        return {}
    
    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        prompt = f"""
        Analyze this job description and extract information in JSON format:
        
        {{
          "required_skills": ["skill1", "skill2"],
          "preferred_skills": ["skill1", "skill2"],
          "experience_years": "X years minimum",
          "education_requirements": "Bachelor's degree preferred",
          "key_responsibilities": ["responsibility1", "responsibility2"],
          "salary_range": "salary info if mentioned",
          "remote_work_policy": "remote/hybrid/onsite",
          "seniority_level": "junior/mid/senior",
          "red_flags": ["concerning requirement if any"],
          "resume_keywords": ["keyword1", "keyword2"]
        }}
        
        Job Description:
        {description}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        ai_analysis = json.loads(response.choices[0].message.content)
        
        # Store in raw_json (Option 1)
        job_posting.raw_json['ai_analysis'] = ai_analysis
        job_posting.raw_json['ai_analyzed_at'] = timezone.now().isoformat()
        job_posting.save()
        
        return ai_analysis
        
    except Exception as e:
        print(f"AI analysis failed for job {job_posting.job_posting_id}: {str(e)}")
        return {}