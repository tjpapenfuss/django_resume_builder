from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
import json
from .models import Experience
from employment.models import Employment
from education.models import Education
from .forms import ExperienceForm
from .services.ai_analyzer import analyze_experience_with_ai, create_skills_from_analysis


@login_required
def experiences(request):
    """Main page: list, filter, and search experiences"""

    # Get filter params from query string (URL)
    filter_type = request.GET.get('type', 'all')
    filter_context = request.GET.get('context', 'all')  # all, employment, education, standalone
    search_query = request.GET.get('search', '')

    # Start with all experiences for the logged-in user
    experiences = Experience.objects.filter(user=request.user)

    # Filter by type if not "all"
    if filter_type != 'all':
        experiences = experiences.filter(experience_type=filter_type)

    # Filter by visibility
    visibility_filter = request.GET.get('visibility', 'all')
    if visibility_filter != 'all':
        experiences = experiences.filter(visibility=visibility_filter)

    # Filter by context (employment, education, standalone)
    if filter_context == 'employment':
        experiences = experiences.filter(employment__isnull=False)
    elif filter_context == 'education':
        experiences = experiences.filter(education__isnull=False)
    elif filter_context == 'standalone':
        experiences = experiences.filter(employment__isnull=True, education__isnull=True)

    # Apply search (title, description, or tags)
    if search_query:
        experiences = experiences.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(tags__icontains=search_query)
        )

    # Sort by most recent first
    experiences = experiences.order_by('-date_started', '-created_date')

    # Choices for dropdown filters
    experience_types = Experience.EXPERIENCE_TYPES

    return render(request, 'list_experience.html', {
        'experiences': experiences,
        'experience_types': experience_types,
        'current_filters': {
            'type': filter_type,
            'context': filter_context,
            'search': search_query,
            'visibility': visibility_filter, 
        }
    })

@login_required
def add_experience(request):
    """Add new experience, with optional skill pre-population"""
    if request.method == 'POST':
        # Handle form submission (existing code)
        form = ExperienceForm(request.POST, user=request.user)
        if form.is_valid():
            experience = form.save(commit=False)
            experience.user = request.user  # attach user to entry
            experience.save()
            
            # Check if user wants AI analysis
            analyze_with_ai = request.POST.get('analyze_with_ai') == 'on'
            
            if analyze_with_ai:
                # Run AI analysis and redirect to skill confirmation page
                return redirect('experience:analyze_experience_skills', experience_id=experience.experience_id)
            else:
                messages.success(request, 'Experience entry added successfully!')
                return redirect('experience:experience')
    else:
        # Pre-populate from URL parameters
        initial_data = {}
        suggested_skill = request.GET.get('skill', '')  # Note: changed from 'suggested_skill'
        
        if suggested_skill:
            initial_data['skills_used_text'] = suggested_skill
            initial_data['tags_text'] = suggested_skill.lower().replace(' ', '-')
        
        form = ExperienceForm(initial=initial_data, user=request.user)
    
    context = {
        'form': form,
        'suggested_skill': suggested_skill,
        'from_skill_analysis': bool(suggested_skill),
    }
    
    return render(request, 'add_experience.html', context)


@login_required
def analyze_experience_skills(request, experience_id):
    """AI analyze experience and let user confirm/modify skills to link"""
    experience = get_object_or_404(Experience, experience_id=experience_id, user=request.user)

    if request.method == 'POST':
        # User is confirming/modifying the AI suggested skills
        action = request.POST.get('action')
        if action == 'accept_all':
            # Handle additional skills from textarea
            additional_skills_text = request.POST.get('additional_skills', '').strip()
            ai_analysis = experience.details.get('ai_analysis', {})
            if additional_skills_text:
                additional_skills = [skill.strip() for skill in additional_skills_text.split('\n') if skill.strip()]
                # Add them to the AI analysis as domain expertise
                if 'domain_expertise' not in ai_analysis:
                    ai_analysis['domain_expertise'] = []
                ai_analysis['domain_expertise'].extend(additional_skills)
            
            result = create_skills_from_analysis(request.user, ai_analysis, experience)
            
            created_count = len(result['created_skills'])
            linked_count = len(result['skill_links'])
            
            messages.success(
                request, 
                f'Successfully created {created_count} new skills and linked {linked_count} skills to your experience!'
            )
            return redirect('experience:experience')
            
        elif action == 'accept_selected':
            selected_skills = request.POST.getlist('selected_skills')
            ai_analysis = experience.details.get('ai_analysis', {})
            
            # Handle additional skills from textarea
            additional_skills_text = request.POST.get('additional_skills', '').strip()
            additional_skills = []
            if additional_skills_text:
                additional_skills = [skill.strip() for skill in additional_skills_text.split('\n') if skill.strip()]
                selected_skills.extend(additional_skills)
            
            # If no AI skills selected but user added custom skills, create minimal analysis
            if not selected_skills and additional_skills:
                # Create a minimal analysis with just the user's skills
                ai_analysis = {
                    'domain_expertise': additional_skills,
                    'skill_categories': {'Other': additional_skills}
                }
                selected_skills = additional_skills
            elif additional_skills:
                # Add custom skills to existing analysis
                if 'domain_expertise' not in ai_analysis:
                    ai_analysis['domain_expertise'] = []
                ai_analysis['domain_expertise'].extend(additional_skills)
            
            # Filter AI analysis to only include selected skills
            filtered_analysis = filter_analysis_by_selection(ai_analysis, selected_skills)
            result = create_skills_from_analysis(request.user, filtered_analysis, experience)
            
            created_count = len(result['created_skills'])
            linked_count = len(result['skill_links'])
            
            messages.success(
                request, 
                f'Successfully created {created_count} new skills and linked {linked_count} skills to your experience!'
            )
            return redirect('experience:experience')
            
        elif action == 'skip':
            # Skip AI analysis
            messages.info(request, 'Experience saved without AI skill analysis.')
            return redirect('experience:experience')
    
    # GET request or initial load - run AI analysis
    ai_analysis = analyze_experience_with_ai(experience)
    if not ai_analysis:
        messages.error(request, 'Unable to analyze experience with AI. Please try again later.')
        return redirect('experience:experience')
    
    # Prepare skills data for template
    skills_data = prepare_skills_for_template(ai_analysis)

    context = {
        'experience': experience,
        'ai_analysis': ai_analysis,
        'skills_data': skills_data,
        'total_skills': sum(len(skills) for skills in skills_data.values()) if skills_data else 0
    }
    
    return render(request, 'analyze_skills.html', context)


@login_required
@require_http_methods(["POST"])
def update_experience(request, experience_id):
    """Edit an existing experience"""
    # Ensure user owns this experience
    experience = get_object_or_404(Experience, experience_id=experience_id, user=request.user)
    form = ExperienceForm(request.POST, instance=experience, user=request.user)

    if form.is_valid():
        form.save()
        messages.success(request, 'Experience entry updated successfully!')
        return redirect('experience:experience')
    else:
        # If request came from AJAX, return JSON errors
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
        else:
            # Otherwise, reload page with form + errors
            experiences = Experience.objects.filter(user=request.user).order_by('-date_started', '-created_date')
            experience_types = Experience.EXPERIENCE_TYPES

            return render(request, 'list_experience.html', {
                'experiences': experiences,
                'form': form,
                'experience_types': experience_types,
                'editing_id': experience_id,
                'current_filters': {
                    'type': 'all',
                    'context': 'all',
                    'search': '',
                    'visibility': 'all',
                }
            })


@login_required
@require_http_methods(["POST"])
def delete_experience(request, experience_id):
    """Delete an experience"""
    experience = get_object_or_404(Experience, experience_id=experience_id, user=request.user)
    experience.delete()
    messages.success(request, 'Experience entry deleted successfully!')
    return redirect('experience:experience')


@login_required
def get_experience_data(request, experience_id):
    """Fetch a single experience's data (for AJAX editing)"""
    experience = get_object_or_404(Experience, experience_id=experience_id, user=request.user)

    # Basic fields
    data = {
        'title': experience.title,
        'description': experience.description,
        'experience_type': experience.experience_type,
        'employment': experience.employment.employment_id if experience.employment else '',
        'education': experience.education.education_id if experience.education else '',
        'date_started': experience.date_started.strftime('%Y-%m-%d') if experience.date_started else '',
        'date_finished': experience.date_finished.strftime('%Y-%m-%d') if experience.date_finished else '',
        'visibility': experience.visibility,
        'skills_used_text': '\n'.join(experience.skills_used or []),
        'tags_text': '\n'.join(experience.tags or []),
    }

    # Extra details
    if experience.details:
        data.update({
            'outcomes': '\n'.join(experience.details.get('outcomes', [])),
            'challenges': '\n'.join(experience.details.get('challenges', [])),
            'tools_used': '\n'.join(experience.details.get('tools_used', [])),
            'team_size': experience.details.get('team_size', ''),
            'budget': experience.details.get('budget', ''),
            'links': '\n'.join(experience.details.get('links', [])),
        })

    return JsonResponse(data)


@login_required
def experience_analytics(request):
    """Basic analytics dashboard for experiences"""
    # Only show public experiences
    experiences = Experience.objects.filter(user=request.user, visibility='public')

    # --- Skills ---
    all_skills = []
    for exp in experiences:
        if exp.skills_used:
            all_skills.extend(exp.skills_used)

    skill_counts = {}
    for skill in all_skills:
        skill_counts[skill] = skill_counts.get(skill, 0) + 1

    # --- Tags ---
    all_tags = []
    for exp in experiences:
        if exp.tags:
            all_tags.extend(exp.tags)

    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # --- Types ---
    type_counts = {}
    for exp in experiences:
        type_counts[exp.experience_type] = type_counts.get(exp.experience_type, 0) + 1

    # --- Context distribution ---
    context_counts = {
        'employment': experiences.filter(employment__isnull=False).count(),
        'education': experiences.filter(education__isnull=False).count(),
        'standalone': experiences.filter(employment__isnull=True, education__isnull=True).count(),
    }

    return render(request, 'experience_analytics.html', {
        'total_experiences': experiences.count(),
        'skill_counts': sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:20],
        'tag_counts': sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:15],
        'type_counts': type_counts,
        'context_counts': context_counts,
    })


@login_required  
def get_experiences_for_resume(request):
    """API: Return experiences tailored for resume generation"""
    job_type = request.GET.get('job_type', '')
    limit = request.GET.get('limit', None)

    # Ensure limit is an integer if provided
    if limit:
        try:
            limit = int(limit)
        except ValueError:
            limit = None

    # Convert job_type into possible tags
    job_type_tags = []
    if job_type:
        job_type_tags = [job_type.lower(), f"{job_type.lower()}-related"]

    # Use model helper to fetch experiences
    experiences = Experience.get_experiences_for_resume(
        user=request.user,
        job_type_tags=job_type_tags,
        limit=limit
    )

    # Serialize into JSON-safe dicts
    experience_data = []
    for exp in experiences:
        data = {
            'id': str(exp.experience_id),
            'title': exp.title,
            'description': exp.description,
            'type': exp.get_experience_type_display(),
            'context': exp.context_name,
            'duration': exp.duration_text,
            'skills': exp.skills_used or [],
            'tags': exp.tags or [],
            'employment_id': str(exp.employment.employment_id) if exp.employment else None,
            'education_id': str(exp.education.education_id) if exp.education else None,
        }

        # Include details if they exist
        if exp.details:
            data['details'] = exp.details

        experience_data.append(data)

    return JsonResponse({
        'experiences': experience_data,
        'total_count': len(experience_data),
        'job_type': job_type,
    })


# Helper functions for AI analysis
def prepare_skills_for_template(ai_analysis):
    """Prepare skills data in a format suitable for the template, grouped by type with deduplication"""
    confidence_scores = ai_analysis.get('confidence_scores', {})
    
    # Use OrderedDict to maintain order with Tools & Technologies first
    from collections import OrderedDict
    skill_groups = OrderedDict([
        ('Tools & Technologies', []),
        ('Technical Skills', []),
        ('Soft Skills', []),
        ('Methodologies', []),
        ('Domain Expertise', []),
        ('Certifications', [])
    ])
    
    # Track seen skills to avoid duplicates
    seen_skills = set()
    
    # Process in priority order - Tools & Technologies first
    priority_order = [
        ('tools_and_technologies', 'Tools & Technologies', 'Technical'),
        ('technical_skills', 'Technical Skills', 'Technical'),
        ('soft_skills', 'Soft Skills', 'Soft Skill'),
        ('methodologies', 'Methodologies', 'Professional'),
        ('domain_expertise', 'Domain Expertise', 'Professional'),
        ('certifications_implied', 'Certifications', 'Professional')
    ]
    
    for skill_type, group_name, display_type in priority_order:
        skills_list = ai_analysis.get(skill_type, [])
        for skill_name in skills_list:
            # Skip if we've already seen this skill (case-insensitive)
            skill_name_lower = skill_name.lower()
            if skill_name_lower in seen_skills:
                continue
            
            seen_skills.add(skill_name_lower)
            
            # Determine confidence based on skill type
            if skill_type == 'technical_skills':
                confidence = 'High' if confidence_scores.get('technical_skills', 0.5) > 0.7 else 'Medium'
            elif skill_type == 'soft_skills':
                confidence = 'High' if confidence_scores.get('soft_skills', 0.5) > 0.7 else 'Medium'
            elif skill_type == 'tools_and_technologies':
                confidence = 'High' if confidence_scores.get('tools_and_technologies', 0.5) > 0.7 else 'Medium'
            else:
                confidence = 'Medium'
            
            skill_groups[group_name].append({
                'name': skill_name,
                'confidence': confidence,
                'type': display_type
            })
    
    # Remove empty groups and return
    return {group: skills for group, skills in skill_groups.items() if skills}


def determine_skill_type_for_display(skill_name, category):
    """Determine skill type for display purposes"""
    skill_name_lower = skill_name.lower()
    category_lower = category.lower()
    
    if category_lower in ['programming', 'technology', 'tools']:
        return 'Technical'
    elif category_lower in ['communication', 'leadership', 'management']:
        return 'Soft Skill'
    elif skill_name_lower in ['python', 'java', 'sql', 'javascript', 'react']:
        return 'Technical'
    elif skill_name_lower in ['leadership', 'communication', 'teamwork']:
        return 'Soft Skill'
    else:
        return 'Professional'


def filter_analysis_by_selection(ai_analysis, selected_skills):
    """Filter AI analysis to only include selected skills"""
    if not selected_skills:
        return {}
    
    filtered_analysis = {
        'skill_categories': {},
        'confidence_scores': ai_analysis.get('confidence_scores', {}),
        'technical_skills': [],
        'soft_skills': [],
        'tools_and_technologies': [],
        'methodologies': [],
        'domain_expertise': []
    }
    
    # Filter skill categories
    skill_categories = ai_analysis.get('skill_categories', {})
    for category, skills in skill_categories.items():
        filtered_skills = [skill for skill in skills if skill in selected_skills]
        if filtered_skills:
            filtered_analysis['skill_categories'][category] = filtered_skills
    
    # Filter direct skill lists
    for skill_type in ['technical_skills', 'soft_skills', 'tools_and_technologies', 'methodologies', 'domain_expertise']:
        skills_list = ai_analysis.get(skill_type, [])
        filtered_skills = [skill for skill in skills_list if skill in selected_skills]
        filtered_analysis[skill_type] = filtered_skills
    
    return filtered_analysis