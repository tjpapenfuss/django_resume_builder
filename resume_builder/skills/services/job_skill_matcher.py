# services/job_skill_matcher.py

from collections import defaultdict, Counter
from django.db.models import Q
from skills.models import Skill
from jobs.models import JobPosting
import difflib

class JobSkillMatcher:
    """
    Analyzes how well a user's skills match a specific job posting
    """
    
    def __init__(self, user, job_posting):
        self.user = user
        self.job_posting = job_posting
        self.user_skills = self._get_user_skills()
        
    def _get_user_skills(self):
        """Get user's current skills normalized for matching"""
        user_skills = Skill.objects.filter(user=self.user)
        
        # Create a mapping of normalized skill names to skill objects
        skill_map = {}
        for skill in user_skills:
            normalized = skill.title.lower().strip()
            skill_map[normalized] = skill
            
            # Also add any alternate names or variations if you have them
            # This could come from skill.details.get('alternates', [])
            alternates = skill.details.get('alternates', []) if skill.details else []
            for alt in alternates:
                skill_map[alt.lower().strip()] = skill
        
        return skill_map
    
    def _get_job_skills(self):
        """Extract skills from job posting (AI or parsed)"""
        job_skills = {
            'required': [],
            'preferred': [],
            'technologies': [],
            'keywords': []
        }
        
        # Use AI analysis if available, otherwise fall back to parsed
        if hasattr(self.job_posting, 'ai_analysis') and self.job_posting.ai_analysis:
            ai_data = self.job_posting.ai_analysis
            job_skills['required'] = [s.lower().strip() for s in ai_data.get('required_skills', [])]
            job_skills['preferred'] = [s.lower().strip() for s in ai_data.get('preferred_skills', [])]
            job_skills['technologies'] = [s.lower().strip() for s in ai_data.get('technologies_mentioned', [])]
            job_skills['keywords'] = [s.lower().strip() for s in ai_data.get('resume_keywords', [])]
        else:
            # Fall back to basic parsed skills
            job_skills['required'] = [s.lower().strip() for s in self.job_posting.required_skills or []]
            job_skills['preferred'] = [s.lower().strip() for s in self.job_posting.preferred_skills or []]
            
        return job_skills
    
    def analyze_match(self):
        """
        Main analysis method that returns comprehensive match data
        """
        job_skills = self._get_job_skills()
        
        # Analyze each skill category
        required_analysis = self._analyze_skill_category(job_skills['required'], 'required')
        preferred_analysis = self._analyze_skill_category(job_skills['preferred'], 'preferred')
        tech_analysis = self._analyze_skill_category(job_skills['technologies'], 'technology')
        
        # Calculate overall match score
        overall_score = self._calculate_overall_score(required_analysis, preferred_analysis, tech_analysis)
        
        # Identify top gaps to address
        top_gaps = self._identify_top_gaps(required_analysis, preferred_analysis, tech_analysis)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(top_gaps, overall_score)
        
        return {
            'overall_match_score': overall_score,
            'required_skills': required_analysis,
            'preferred_skills': preferred_analysis,
            'technologies': tech_analysis,
            'top_skill_gaps': top_gaps,
            'recommendations': recommendations,
            'match_level': self._get_match_level(overall_score),
            'total_job_skills': len(job_skills['required']) + len(job_skills['preferred']) + len(job_skills['technologies']),
            'total_matched_skills': required_analysis['matched_count'] + preferred_analysis['matched_count'] + tech_analysis['matched_count']
        }
    
    def _analyze_skill_category(self, job_skills_list, category):
        """Analyze a specific category of skills (required, preferred, etc.)"""
        if not job_skills_list:
            return {
                'total_count': 0,
                'matched_count': 0,
                'matched_skills': [],
                'missing_skills': [],
                'partial_matches': [],
                'match_percentage': 0
            }
        
        matched_skills = []
        missing_skills = []
        partial_matches = []
        
        for job_skill in job_skills_list:
            if not job_skill:  # Skip empty strings
                continue
                
            match_result = self._find_skill_match(job_skill)
            
            if match_result['type'] == 'exact':
                matched_skills.append({
                    'job_skill': job_skill,
                    'user_skill': match_result['user_skill'],
                    'match_type': 'exact'
                })
            elif match_result['type'] == 'partial':
                partial_matches.append({
                    'job_skill': job_skill,
                    'user_skill': match_result['user_skill'],
                    'match_type': 'partial',
                    'similarity': match_result['similarity']
                })
            else:
                missing_skills.append({
                    'skill_name': job_skill.title(),
                    'priority': self._calculate_skill_priority(job_skill, category),
                    'category': category,
                    'suggested_category': self._suggest_skill_category(job_skill)
                })
        
        total_count = len(job_skills_list)
        matched_count = len(matched_skills) + len(partial_matches)
        match_percentage = (matched_count / total_count * 100) if total_count > 0 else 0
        
        return {
            'total_count': total_count,
            'matched_count': matched_count,
            'matched_skills': matched_skills,
            'missing_skills': missing_skills,
            'partial_matches': partial_matches,
            'match_percentage': round(match_percentage, 1)
        }
    
    def _find_skill_match(self, job_skill):
        """Find if user has this skill (exact or partial match)"""
        job_skill_lower = job_skill.lower().strip()
        
        # Check for exact match
        if job_skill_lower in self.user_skills:
            return {
                'type': 'exact',
                'user_skill': self.user_skills[job_skill_lower],
                'similarity': 100
            }
        
        # Check for partial matches using fuzzy matching
        best_match = None
        best_similarity = 0
        
        for user_skill_name, user_skill_obj in self.user_skills.items():
            similarity = difflib.SequenceMatcher(None, job_skill_lower, user_skill_name).ratio()
            
            if similarity > 0.8 and similarity > best_similarity:  # 80% similarity threshold
                best_match = user_skill_obj
                best_similarity = similarity
        
        if best_match:
            return {
                'type': 'partial',
                'user_skill': best_match,
                'similarity': round(best_similarity * 100, 1)
            }
        
        return {'type': 'none'}
    
    def _calculate_overall_score(self, required_analysis, preferred_analysis, tech_analysis):
        """Calculate weighted overall match score"""
        # Weight required skills more heavily
        required_weight = 0.6
        preferred_weight = 0.3
        tech_weight = 0.1
        
        required_score = required_analysis['match_percentage'] * required_weight
        preferred_score = preferred_analysis['match_percentage'] * preferred_weight
        tech_score = tech_analysis['match_percentage'] * tech_weight
        
        return round(required_score + preferred_score + tech_score, 1)
    
    def _identify_top_gaps(self, required_analysis, preferred_analysis, tech_analysis, limit=5):
        """Identify the most important skill gaps with custom priority hierarchy"""
        all_gaps = []
        
        # Get keywords from job analysis if available
        keywords_analysis = {'missing_skills': []}
        if hasattr(self.job_posting, 'ai_analysis') and self.job_posting.ai_analysis:
            ai_keywords = self.job_posting.ai_analysis.get('resume_keywords', [])
            if ai_keywords:
                # Get existing required skill names for comparison
                existing_required_names = set()
                for skill_dict in required_analysis.get('missing_skills', []):
                    if isinstance(skill_dict, dict):
                        existing_required_names.add(skill_dict.get('skill_name', '').lower().strip())
                
                keyword_gaps = []
                for keyword in ai_keywords:
                    keyword_lower = keyword.lower().strip()
                    # Only add if not already in required skills and user doesn't have it
                    if (keyword_lower not in existing_required_names and 
                        keyword_lower not in self.user_skills):
                        keyword_gaps.append({
                            'skill_name': keyword.title(),
                            'priority': 'high',
                            'category': 'keyword',
                            'suggested_category': self._suggest_skill_category(keyword)
                        })
                
                keywords_analysis = {'missing_skills': keyword_gaps}
        
        # Priority 1: Technologies (highest priority - score 100)
        for gap in tech_analysis['missing_skills']:
            gap['priority_score'] = 100
            gap['priority'] = 'critical'
            gap['category'] = 'technology'
            all_gaps.append(gap)
        
        # Priority 2: Required skills (score 90)
        for gap in required_analysis['missing_skills']:
            gap['priority_score'] = 90
            gap['priority'] = 'critical'
            gap['category'] = 'required'
            all_gaps.append(gap)
        
        # Priority 3: Keywords not in required (score 70)
        for gap in keywords_analysis['missing_skills']:
            gap['priority_score'] = 70
            gap['priority'] = 'high'
            gap['category'] = 'keyword'
            all_gaps.append(gap)
        
        # Priority 4: Preferred skills (lowest priority - score 50)
        for gap in preferred_analysis['missing_skills']:
            gap['priority_score'] = 50
            gap['priority'] = 'medium'
            gap['category'] = 'preferred'
            all_gaps.append(gap)
        
        # Remove duplicates (keep higher priority version)
        seen_skills = {}
        unique_gaps = []
        
        for gap in all_gaps:
            skill_name_lower = gap['skill_name'].lower()
            if skill_name_lower not in seen_skills or gap['priority_score'] > seen_skills[skill_name_lower]['priority_score']:
                seen_skills[skill_name_lower] = gap
        
        unique_gaps = list(seen_skills.values())
        
        # Sort by priority score (high to low), then by skill name for consistency
        unique_gaps.sort(key=lambda x: (-x['priority_score'], x['skill_name']))
        
        return unique_gaps
    
    def _calculate_skill_priority(self, skill, category):
        """Calculate priority level for missing skill"""
        if category == 'required':
            return 'critical'
        elif category == 'preferred':
            return 'high'
        else:
            return 'medium'
    
    def _suggest_skill_category(self, skill_name):
        """Suggest what category this skill should be in"""
        skill_lower = skill_name.lower()
        
        technical_keywords = ['python', 'javascript', 'sql', 'aws', 'docker', 'api', 'framework', 'database']
        if any(keyword in skill_lower for keyword in technical_keywords):
            return 'Programming'
        
        leadership_keywords = ['leadership', 'management', 'team', 'mentor', 'lead']
        if any(keyword in skill_lower for keyword in leadership_keywords):
            return 'Leadership'
        
        communication_keywords = ['communication', 'presentation', 'writing', 'documentation']
        if any(keyword in skill_lower for keyword in communication_keywords):
            return 'Communication'
        
        return 'Other'
    
    def _generate_recommendations(self, top_gaps, overall_score):
        """Generate actionable recommendations"""
        recommendations = []
        
        if overall_score < 40:
            recommendations.append({
                'type': 'urgent',
                'message': f"Your skill match is quite low at {overall_score}%. Consider adding experiences that demonstrate the critical missing skills.",
                'action': 'Focus on required skills first'
            })
        elif overall_score < 70:
            recommendations.append({
                'type': 'moderate',
                'message': f"You have a {overall_score}% match. Adding a few key experiences could significantly improve your candidacy.",
                'action': 'Add experiences for top missing skills'
            })
        else:
            recommendations.append({
                'type': 'good',
                'message': f"Strong {overall_score}% skill match! Consider adding experiences for preferred skills to stand out.",
                'action': 'Optimize with preferred skills'
            })
        
        # Add specific skill recommendations
        if top_gaps:
            skill_names = [gap['skill_name'] for gap in top_gaps[:3]]
            recommendations.append({
                'type': 'skills',
                'message': f"Priority skills to add: {', '.join(skill_names)}",
                'action': f"Create experiences showcasing these {len(skill_names)} skills"
            })
        
        return recommendations
    
    def _get_match_level(self, score):
        """Convert numeric score to text level"""
        if score >= 80:
            return 'excellent'
        elif score >= 70:
            return 'good'
        elif score >= 50:
            return 'fair'
        else:
            return 'poor'
    
    def get_experience_suggestions(self, skill_name):
        """Generate specific prompts for adding experiences for a missing skill"""
        return {
            'skill_name': skill_name.title(),
            'prompts': [
                f"Describe a project where you used {skill_name} to solve a problem",
                f"Think of a time when you learned {skill_name} quickly to meet a deadline", 
                f"Explain a situation where your {skill_name} skills made a significant impact",
                f"Share an example of how you've applied {skill_name} in a team setting"
            ],
            'suggested_action': f"Add an experience that highlights your {skill_name} capabilities"
        }
