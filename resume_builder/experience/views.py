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

    # Create empty form for adding a new experience
    form = ExperienceForm(user=request.user)

    # Choices for dropdown filters
    experience_types = Experience.EXPERIENCE_TYPES

    return render(request, 'experiences.html', {
        'experiences': experiences,
        'form': form,
        'experience_types': experience_types,
        'current_filters': {
            'type': filter_type,
            'context': filter_context,
            'search': search_query,
        }
    })

@login_required
@require_http_methods(["POST"])
def add_experience(request):
    """Add a new experience"""
    form = ExperienceForm(request.POST, user=request.user)
    if form.is_valid():
        experience = form.save(commit=False)
        experience.user = request.user  # attach user to entry
        experience.save()
        messages.success(request, 'Experience entry added successfully!')
        return redirect('experiences')
    else:
        # If invalid, reload page with errors + current experiences
        experiences = Experience.objects.filter(user=request.user).order_by('-date_started', '-created_date')
        experience_types = Experience.EXPERIENCE_TYPES

        return render(request, 'experiences.html', {
            'experiences': experiences,
            'form': form,
            'experience_types': experience_types,
            'current_filters': {
                'type': 'all',
                'context': 'all',
                'search': '',
            }
        })


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
        return redirect('experiences')
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

            return render(request, 'experiences.html', {
                'experiences': experiences,
                'form': form,
                'experience_types': experience_types,
                'editing_id': experience_id,
                'current_filters': {
                    'type': 'all',
                    'context': 'all',
                    'search': '',
                }
            })

@login_required
@require_http_methods(["POST"])
def delete_experience(request, experience_id):
    """Delete an experience"""
    experience = get_object_or_404(Experience, experience_id=experience_id, user=request.user)
    experience.delete()
    messages.success(request, 'Experience entry deleted successfully!')
    return redirect('experiences')

@login_required
def get_experience_data(request, experience_id):
    """Fetch a single experience’s data (for AJAX editing)"""
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
