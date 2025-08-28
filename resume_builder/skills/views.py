from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db.models import Q, Count
from django.urls import reverse
from django.utils import timezone
from django.db import transaction

from .models import Skill, SkillAnalysis, ExperienceSkill
from .forms import SkillForm, SkillFilterForm
from .services.skill_analysis import SkillGapAnalyzer
from experience.models import Experience
from jobs.models import JobApplication
import json
import logging

logger = logging.getLogger(__name__)

@login_required
def skills(request):
    """Enhanced skill management view with experience connections"""
    # Initialize forms
    skill_form = SkillForm(user=request.user)
    filter_form = SkillFilterForm(request.GET, user=request.user)
    
    # Start with user's skills, include experience count
    skills = Skill.objects.filter(user=request.user).prefetch_related('experiences')
    
    # Apply filters if form is valid
    if filter_form.is_valid():
        # Search filter
        search_query = filter_form.cleaned_data.get('search')
        if search_query:
            skills = skills.filter(
                Q(title__icontains=search_query) |
                Q(category__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Category filter
        category_filter = filter_form.cleaned_data.get('category')
        if category_filter:
            skills = skills.filter(category__iexact=category_filter)
        
        # Skill type filter
        skill_type_filter = filter_form.cleaned_data.get('skill_type')
        if skill_type_filter:
            skills = skills.filter(skill_type=skill_type_filter)
        
        # Skill level filter
        skill_level_filter = filter_form.cleaned_data.get('skill_level')
        if skill_level_filter:
            skills = skills.filter(skill_level=skill_level_filter)
        
        # Sorting
        sort_by = filter_form.cleaned_data.get('sort_by')
        if sort_by:
            skills = skills.order_by(sort_by)
        else:
            skills = skills.order_by('-created_date')
    else:
        skills = skills.order_by('-created_date')
    
    # Get existing categories for the user
    existing_categories = list(filter_form.get_existing_categories())
    predefined_categories = [choice[0] for choice in Skill.SKILL_CATEGORIES]
    
    # Check for recent skill analysis
    latest_analysis = SkillAnalysis.objects.filter(user=request.user).first()
    
    context = {
        'skills': skills,
        'form': skill_form,
        'filter_form': filter_form,
        'existing_categories': existing_categories,
        'predefined_categories': predefined_categories,
        'latest_analysis': latest_analysis,
        'total_experiences': Experience.objects.filter(user=request.user).count(),
    }
    
    return render(request, 'skills/skills.html', context)

@login_required
@require_http_methods(["POST"])
def run_skill_analysis(request):
    """AJAX endpoint to run skill gap analysis and save results"""
    try:
        print("Starting skills analysis.")
        # Validate user has required data
        experience_count = Experience.objects.filter(user=request.user).count()
        job_count = JobApplication.objects.filter(user=request.user).count()
        
        if experience_count == 0 or job_count == 0:
            return JsonResponse({
                'success': False,
                'error': 'insufficient_data',
                'message': f'You need at least 1 experience and 1 saved job. You have {experience_count} experiences and {job_count} jobs.',
                'experience_count': experience_count,
                'job_count': job_count
            })
        
        # Initialize analyzer
        analyzer = SkillGapAnalyzer(request.user)
        
        # Run analysis steps
        logger.info(f"Starting skill analysis for user {request.user.user_id}")
        
        # Step 1: Extract skills from experiences
        new_skills = analyzer.extract_skills_from_experiences()
        logger.info(f"Extracted {len(new_skills)} new skills")
        
        # Step 2: Calculate skill gaps
        skill_gaps = analyzer.calculate_skill_gaps()
        
        # Step 3: Calculate job matches
        job_matches = analyzer.calculate_job_match_scores()
        
        # Step 4: Get current skill count
        total_skills = Skill.objects.filter(user=request.user).count()
        
        # Step 5: Save analysis to database
        with transaction.atomic():
            analysis = SkillAnalysis.objects.create(
                user=request.user,
                total_experiences_analyzed=experience_count,
                total_jobs_analyzed=job_count,
                total_skills_found=total_skills,
                new_skills_created=len(new_skills),
                total_skill_gaps=len(skill_gaps),
                average_job_match_score=round(
                    sum(job['match_percentage'] for job in job_matches) / len(job_matches)
                    if job_matches else 0, 2
                ),
                highest_job_match_score=max(
                    (job['match_percentage'] for job in job_matches), default=0
                ),
                lowest_job_match_score=min(
                    (job['match_percentage'] for job in job_matches), default=0
                ),
                skill_gaps=skill_gaps,
                job_matches=[
                    {
                        'job_id': str(job['job'].job_posting_id),
                        'job_title': job['job'].job_title,
                        'company_name': job['job'].company_name,
                        'match_percentage': job['match_percentage'],
                        'matched_skills': job['matched_skills'],
                        'missing_skills': job['missing_skills'],
                        'total_job_skills': job['total_job_skills'],
                        'total_matched': job['total_matched']
                    }
                    for job in job_matches
                ],
                skills_extracted=[skill.title for skill in new_skills],
                analysis_parameters={
                    'analyzer_version': '1.0',
                    'extraction_method': 'automated',
                    'include_tags': True,
                    'include_descriptions': True
                }
            )
        
        logger.info(f"Analysis completed and saved with ID {analysis.analysis_id}")
        
        return JsonResponse({
            'success': True,
            'analysis_id': str(analysis.analysis_id),
            'new_skills_created': len(new_skills),
            'skill_gaps_found': len(skill_gaps),
            'redirect_url': reverse('skills:skill_analysis_detail', args=[analysis.analysis_id])
        })
        
    except Exception as e:
        logger.error(f"Skill analysis failed for user {request.user.user_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'analysis_failed',
            'message': f'Analysis failed: {str(e)}'
        }, status=500)

@login_required
def skill_analysis_detail(request, analysis_id):
    """Display detailed skill analysis results"""
    analysis = get_object_or_404(
        SkillAnalysis,
        analysis_id=analysis_id,
        user=request.user
    )
    
    # Mark as in progress if fresh
    if analysis.status == 'fresh':
        analysis.mark_in_progress()
    
    context = {
        'analysis': analysis,
        'top_skill_gaps': analysis.top_skill_gaps,
        'job_matches': analysis.job_matches,
        'can_refresh': analysis.needs_refresh,
    }
    
    return render(request, 'skills/analysis_detail.html', context)

@login_required
def add_experience_for_skill(request, skill_id):
    """Redirect to experience form with skill pre-populated"""
    skill = get_object_or_404(Skill, skill_id=skill_id, user=request.user)
    
    # Build URL with parameters
    url = reverse('add_experience')
    params = [
        f'suggested_skill={skill.title}',
        f'story_prompt=Think of a specific situation where you demonstrated your {skill.title} skills. Focus on the actions you took and the results you achieved.',
        f'skill_id={skill_id}'
    ]
    
    url += '?' + '&'.join(params)
    return redirect(url)

@login_required
@require_http_methods(["POST"])
def link_experience_to_skill(request, skill_id):
    """Link an existing experience to a skill"""
    skill = get_object_or_404(Skill, skill_id=skill_id, user=request.user)
    experience_id = request.POST.get('experience_id')
    prominence = request.POST.get('prominence', 'secondary')
    
    if not experience_id:
        return JsonResponse({'success': False, 'error': 'No experience selected'})
    
    try:
        experience = Experience.objects.get(
            experience_id=experience_id,
            user=request.user
        )
        
        # Create the relationship
        experience_skill, created = ExperienceSkill.objects.get_or_create(
            experience=experience,
            skill=skill,
            defaults={
                'prominence': prominence,
                'extraction_method': 'manual'
            }
        )
        
        if created:
            messages.success(request, f'Linked "{experience.title}" to "{skill.title}"')
            return JsonResponse({'success': True, 'created': True})
        else:
            return JsonResponse({'success': False, 'error': 'Experience already linked to this skill'})
            
    except Experience.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Experience not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def skill_analysis_history(request):
    """Show user's skill analysis history"""
    analyses = SkillAnalysis.objects.filter(user=request.user)
    
    context = {
        'analyses': analyses,
        'total_analyses': analyses.count(),
    }
    
    return render(request, 'skills/analysis_history.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def add_skill(request):
    """Add new skill entry"""
    if request.method == 'POST':
        form = SkillForm(request.POST, user=request.user)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.user = request.user
            try:
                skill.full_clean()
                skill.save()
                messages.success(request, 'Skill added successfully!')
                return redirect('skills:skills')
            except ValidationError as e:
                if hasattr(e, 'error_dict'):
                    for field, errors in e.error_dict.items():
                        form.add_error(field, errors)
                else:
                    form.add_error(None, str(e))
    else:
        # GET request - show empty form
        form = SkillForm(user=request.user)
    
    # Get data needed for the template
    existing_categories = list(Skill.objects.filter(user=request.user).values_list('category', flat=True).distinct())
    predefined_categories = [choice[0] for choice in Skill.SKILL_CATEGORIES]
    
    return render(request, 'skills/add_skill.html', {
        'form': form,
        'existing_categories': existing_categories,
        'predefined_categories': predefined_categories,
    })

@login_required
@require_http_methods(["POST"])
def update_skill(request, skill_id):
    """Update existing skill entry"""
    skill = get_object_or_404(Skill, skill_id=skill_id, user=request.user)
    form = SkillForm(request.POST, instance=skill, user=request.user)
    
    if form.is_valid():
        skill = form.save(commit=False)
        try:
            skill.full_clean()
            skill.save()
            messages.success(request, 'Skill updated successfully!')
            return redirect('skills:skills')
        except ValidationError as e:
            form.add_error(None, e)
    
    # Handle AJAX form error responses
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'errors': form.errors
        })
    else:
        filter_form = SkillFilterForm(user=request.user)
        skills = Skill.objects.filter(user=request.user).order_by('-created_date')
        
        existing_categories = list(Skill.objects.filter(user=request.user).values_list('category', flat=True).distinct())
        predefined_categories = [choice[0] for choice in Skill.SKILL_CATEGORIES]
        latest_analysis = SkillAnalysis.objects.filter(user=request.user).first()
        
        return render(request, 'skills/skills.html', {
            'skills': skills,
            'form': form,
            'filter_form': filter_form,
            'editing_id': skill_id,
            'existing_categories': existing_categories,
            'predefined_categories': predefined_categories,
            'latest_analysis': latest_analysis,
            'total_experiences': Experience.objects.filter(user=request.user).count(),
        })

@login_required
@require_http_methods(["POST"])
def delete_skill(request, skill_id):
    """Delete skill entry - also removes experience relationships"""
    skill = get_object_or_404(Skill, skill_id=skill_id, user=request.user)
    
    # Get count of linked experiences for the message
    experience_count = skill.experiences.count()
    
    skill_title = skill.title
    skill.delete()  # This will also delete ExperienceSkill relationships due to CASCADE
    
    if experience_count > 0:
        messages.success(
            request, 
            f'Skill "{skill_title}" and {experience_count} experience link(s) deleted successfully!'
        )
    else:
        messages.success(request, f'Skill "{skill_title}" deleted successfully!')
    
    return redirect('skills:skills')

@login_required
def get_skill_data(request, skill_id):
    """Get skill data for editing (AJAX endpoint) - enhanced with experience info"""
    skill = get_object_or_404(Skill, skill_id=skill_id, user=request.user)
    
    data = {
        'category': skill.category,
        'skill_type': skill.skill_type or '',
        'title': skill.title or '',
        'description': skill.description or '',
        'skill_level': skill.skill_level or '',
        'years_experience': skill.years_experience or '',
        'experience_count': skill.experience_count,
        'proficiency_score': skill.get_proficiency_score(),
    }
    
    # Add details JSON data
    if skill.details:
        # Convert lists back to newline-separated strings for the form
        if 'certifications' in skill.details:
            data['certifications'] = '\n'.join(skill.details['certifications'])
        if 'projects' in skill.details:
            data['projects'] = '\n'.join(skill.details['projects'])
    
    return JsonResponse(data)

@login_required
def get_user_categories(request):
    """AJAX endpoint to get user's existing categories"""
    categories = list(
        Skill.objects.filter(user=request.user)
        .values_list('category', flat=True)
        .distinct()
        .order_by('category')
    )
    return JsonResponse({'categories': categories})

@login_required
def get_user_experiences(request):
    """AJAX endpoint to get user's experiences for linking to skills"""
    experiences = Experience.objects.filter(user=request.user).values(
        'experience_id', 'title', 'title', 'employment', 'education'
    )
    return JsonResponse({'experiences': list(experiences)})

