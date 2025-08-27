# services/skill_analysis.py

from collections import defaultdict, Counter
from django.db.models import Count, Q
from experience.models import Experience
from skills.models import Skill
from jobs.models import JobPosting, JobApplication

import re

class SkillGapAnalyzer:
    """
    Analyzes user experiences to extract skills, then identifies gaps 
    against their saved/applied jobs
    """
    
    def __init__(self, user):
        self.user = user
        
    def extract_skills_from_experiences(self):
        """
        Step 1: Extract and create skills from user's existing experiences
        Returns: List of newly created skills
        """
        experiences = Experience.objects.filter(
            user=self.user,
            visibility__in=['public', 'private']  # Skip drafts
        )
        
        skill_mentions = defaultdict(list)  # skill_name -> [experience_ids]
        
        for exp in experiences:
            # Extract from skills_used JSON field
            for skill in exp.skills_used:
                skill_mentions[skill.lower().strip()].append(str(exp.experience_id))  # Convert to string
            
            # Extract from tags
            for tag in exp.tags:
                skill_mentions[tag.lower().strip()].append(str(exp.experience_id))  # Convert to string
            
            # Extract from description using basic NLP
            extracted_skills = self._extract_skills_from_text(exp.description)
            for skill in extracted_skills:
                skill_mentions[skill.lower().strip()].append(str(exp.experience_id))  # Convert to string
        
        # Create/update skills in database
        created_skills = []
        for skill_name, experience_ids in skill_mentions.items():
            skill_name_clean = skill_name.title()
            
            # Get or create the skill
            skill, created = Skill.objects.get_or_create(
                user=self.user,
                title=skill_name_clean,
                defaults={
                    'category': self._categorize_skill(skill_name_clean),
                    'skill_type': self._determine_skill_type(skill_name_clean),
                    'years_experience': self._estimate_years_experience(experience_ids),
                    'details': {
                        'extracted_from_experiences': [str(exp_id) for exp_id in set(experience_ids)],  # Convert to strings
                        'mention_count': len(experience_ids)
                    }
                }
            )

            if created:
                created_skills.append(skill)
            else:
                # Update existing skill with new experience references
                existing_exp_ids = set(skill.details.get('extracted_from_experiences', []))
                new_exp_ids = set(str(exp_id) for exp_id in experience_ids)  # Convert to strings
                all_exp_ids = existing_exp_ids.union(new_exp_ids)
                
                skill.details.update({
                    'extracted_from_experiences': list(all_exp_ids),
                    'mention_count': len(all_exp_ids)
                })
                skill.save()
        
        return created_skills
    
    def analyze_job_skill_requirements(self):
        """
        Step 2: Analyze all user's saved/applied jobs to identify required skills
        Returns: Dict with skill frequency analysis
        """
        # Get user's jobs (saved or applied)
        user_applications = JobApplication.objects.filter(user=self.user)
        job_postings = [app.job_posting for app in user_applications]
        
        if not job_postings:
            return {}
        
        # Aggregate skills across all jobs
        skill_frequency = Counter()
        job_skill_details = []
        
        for job in job_postings:
            job_skills = []
            
            # Get AI-analyzed skills if available
            if job.has_ai_analysis:
                job_skills.extend(job.ai_required_skills)
                job_skills.extend(job.ai_preferred_skills)
            else:
                # Fallback to basic parsed skills
                job_skills.extend(job.required_skills)
                job_skills.extend(job.preferred_skills)
            
            # Clean and normalize skill names
            normalized_skills = [skill.lower().strip() for skill in job_skills if skill]
            
            for skill in normalized_skills:
                skill_frequency[skill] += 1
            
            job_skill_details.append({
                'job': job,
                'skills': normalized_skills,
                'skill_count': len(normalized_skills)
            })
        
        return {
            'skill_frequency': dict(skill_frequency),
            'job_details': job_skill_details,
            'total_jobs_analyzed': len(job_postings)
        }
    
    def calculate_skill_gaps(self):
        """
        Step 3: Compare user skills against job requirements
        Returns: Prioritized list of skill gaps
        """
        # Get user's current skills
        user_skills = set(
            skill.title.lower().strip() 
            for skill in Skill.objects.filter(user=self.user)
        )
        
        # Get job requirements
        job_analysis = self.analyze_job_skill_requirements()
        if not job_analysis:
            return []
        
        skill_frequency = job_analysis['skill_frequency']
        
        # Find gaps: skills mentioned in jobs but missing from user profile
        skill_gaps = []
        for job_skill, frequency in skill_frequency.items():
            if job_skill not in user_skills:
                # Calculate priority score
                priority_score = self._calculate_gap_priority(
                    job_skill, 
                    frequency, 
                    job_analysis['total_jobs_analyzed']
                )
                
                skill_gaps.append({
                    'skill_name': job_skill.title(),
                    'frequency': frequency,
                    'percentage_of_jobs': (frequency / job_analysis['total_jobs_analyzed']) * 100,
                    'priority_score': priority_score,
                    'suggested_category': self._categorize_skill(job_skill),
                    'skill_type': self._determine_skill_type(job_skill)
                })
        
        # Sort by priority score (high to low)
        skill_gaps.sort(key=lambda x: x['priority_score'], reverse=True)
        
        return skill_gaps
    
    def calculate_job_match_scores(self):
        """
        Step 4: Score how well user matches each saved job
        Returns: List of jobs with match scores
        """
        user_skills = set(
            skill.title.lower().strip() 
            for skill in Skill.objects.filter(user=self.user)
        )
        
        user_applications = JobApplication.objects.filter(user=self.user)
        job_scores = []
        
        for app in user_applications:
            job = app.job_posting
            job_skills = []
            
            # Get job skills
            if job.has_ai_analysis:
                job_skills.extend([s.lower().strip() for s in job.ai_required_skills])
                job_skills.extend([s.lower().strip() for s in job.ai_preferred_skills])
            else:
                job_skills.extend([s.lower().strip() for s in job.required_skills])
                job_skills.extend([s.lower().strip() for s in job.preferred_skills])
            
            job_skills = set(job_skills)
            
            if job_skills:
                # Calculate match percentage
                matched_skills = user_skills.intersection(job_skills)
                match_percentage = (len(matched_skills) / len(job_skills)) * 100
                
                missing_skills = job_skills - user_skills
                
                job_scores.append({
                    'job': job,
                    'application': app,
                    'match_percentage': round(match_percentage, 1),
                    'matched_skills': list(matched_skills),
                    'missing_skills': list(missing_skills),
                    'total_job_skills': len(job_skills),
                    'total_matched': len(matched_skills)
                })
        
        # Sort by match percentage (high to low)
        job_scores.sort(key=lambda x: x['match_percentage'], reverse=True)
        
        return job_scores
    
    def get_story_suggestions_for_job(self, job_posting, top_n=3):
        """
        Step 5: For a specific job, suggest which skill gaps need stories
        Returns: Prioritized list of skills that need experience stories
        """
        # Get job's required skills
        job_skills = []
        if job_posting.has_ai_analysis:
            job_skills.extend([s.lower().strip() for s in job_posting.ai_required_skills])
            job_skills.extend([s.lower().strip() for s in job_posting.ai_preferred_skills])
        else:
            job_skills.extend([s.lower().strip() for s in job_posting.required_skills])
            job_skills.extend([s.lower().strip() for s in job_posting.preferred_skills])
        
        # Get user's current skills
        user_skills = {
            skill.title.lower().strip(): skill 
            for skill in Skill.objects.filter(user=self.user)
        }
        
        # Find missing skills for this specific job
        missing_skills = []
        for job_skill in job_skills:
            if job_skill not in user_skills:
                missing_skills.append({
                    'skill_name': job_skill.title(),
                    'suggestion_prompt': self._generate_story_prompt(job_skill, job_posting),
                    'skill_type': self._determine_skill_type(job_skill),
                    'priority': 'high' if job_skill in job_posting.ai_required_skills else 'medium'
                })
        
        return missing_skills[:top_n]
    
    # Helper methods
    def _extract_skills_from_text(self, text):
        """Basic skill extraction from text using patterns"""
        # This is a simplified version - you could use more sophisticated NLP
        common_skills = [
            'python', 'javascript', 'react', 'django', 'sql', 'aws', 'docker',
            'leadership', 'project management', 'agile', 'scrum', 'git',
            'communication', 'problem solving', 'teamwork', 'analysis'
        ]
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in common_skills:
            if skill in text_lower:
                found_skills.append(skill)
        
        return found_skills
    
    def _categorize_skill(self, skill_name):
        """Categorize skill based on name"""
        skill_lower = skill_name.lower()
        
        technical_keywords = ['python', 'javascript', 'java', 'sql', 'aws', 'docker', 'react', 'django']
        leadership_keywords = ['leadership', 'management', 'team', 'mentor']
        communication_keywords = ['communication', 'presentation', 'writing']
        
        if any(keyword in skill_lower for keyword in technical_keywords):
            return 'Programming'
        elif any(keyword in skill_lower for keyword in leadership_keywords):
            return 'Leadership'
        elif any(keyword in skill_lower for keyword in communication_keywords):
            return 'Communication'
        else:
            return 'Other'
    
    def _determine_skill_type(self, skill_name):
        """Determine if skill is technical, soft, etc."""
        skill_lower = skill_name.lower()
        
        technical_keywords = ['python', 'javascript', 'sql', 'aws', 'docker', 'api', 'framework']
        if any(keyword in skill_lower for keyword in technical_keywords):
            return 'Technical'
        
        soft_keywords = ['communication', 'leadership', 'teamwork', 'problem solving']
        if any(keyword in skill_lower for keyword in soft_keywords):
            return 'Soft'
        
        return 'Transferable'
    
    def _estimate_years_experience(self, experience_ids):
        """Estimate years of experience based on linked experiences"""
        experiences = Experience.objects.filter(
            experience_id__in=experience_ids,
            date_started__isnull=False
        )
        
        if not experiences:
            return 1
        
        # Simple estimation: count unique years mentioned
        years = set()
        for exp in experiences:
            start_year = exp.date_started.year
            end_year = exp.date_finished.year if exp.date_finished else 2024
            years.update(range(start_year, end_year + 1))
        
        return min(len(years), 10)  # Cap at 10 years
    
    def _calculate_gap_priority(self, skill, frequency, total_jobs):
        """Calculate priority score for skill gap"""
        percentage = (frequency / total_jobs) * 100
        
        # Higher frequency = higher priority
        # Technical skills get slight boost
        base_score = percentage
        
        if self._determine_skill_type(skill) == 'Technical':
            base_score *= 1.2
        
        return round(base_score, 2)
    
    def _generate_story_prompt(self, skill, job_posting):
        """Generate a prompt to help user create a story for missing skill"""
        return f"Think of a time when you demonstrated {skill.title()} skills. This could be from work, projects, volunteering, or education. Focus on a specific situation where you used {skill} to solve a problem or achieve a result."


# views.py - Example usage
class SkillGapAnalysisView:
    """Example view showing how to use the analyzer"""
    
    def analyze_user_skills(self, user):
        analyzer = SkillGapAnalyzer(user)
        
        # Step 1: Extract skills from experiences
        new_skills = analyzer.extract_skills_from_experiences()
        
        # Step 2: Find gaps
        skill_gaps = analyzer.calculate_skill_gaps()
        
        # Step 3: Calculate job matches
        job_matches = analyzer.calculate_job_match_scores()
        
        return {
            'new_skills_created': len(new_skills),
            'top_skill_gaps': skill_gaps[:5],
            'job_match_scores': job_matches,
            'suggestions': self._generate_user_suggestions(skill_gaps, job_matches)
        }
    
    def _generate_user_suggestions(self, skill_gaps, job_matches):
        """Generate user-friendly suggestions"""
        suggestions = []
        
        if skill_gaps:
            top_gaps = skill_gaps[:3]
            suggestions.append({
                'type': 'skill_gaps',
                'message': f"You're missing {len(skill_gaps)} skills that appear frequently in your saved jobs. The top ones are: {', '.join([gap['skill_name'] for gap in top_gaps])}",
                'action': 'Add experiences that demonstrate these skills'
            })
        
        low_match_jobs = [job for job in job_matches if job['match_percentage'] < 60]
        if low_match_jobs:
            suggestions.append({
                'type': 'low_matches',
                'message': f"You have {len(low_match_jobs)} saved jobs where you match less than 60% of requirements.",
                'action': 'Consider adding more relevant experiences or skills'
            })
        
        return suggestions