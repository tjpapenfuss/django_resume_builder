from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import Skill
from .forms import SkillForm, SkillFilterForm


@login_required
def skills(request):
    """Skill management view with filtering and searching"""
    # Initialize forms
    skill_form = SkillForm(user=request.user)
    filter_form = SkillFilterForm(request.GET, user=request.user)
    
    # Start with user's skills
    skills = Skill.objects.filter(user=request.user)
    
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
    
    return render(request, 'skills.html', {
        'skills': skills,
        'form': skill_form,
        'filter_form': filter_form,
        'existing_categories': existing_categories,
        'predefined_categories': predefined_categories,
    })


@login_required
@require_http_methods(["POST"])
def add_skill(request):
    """Add new skill entry"""
    form = SkillForm(request.POST, user=request.user)
    if form.is_valid():
        skill = form.save(commit=False)
        skill.user = request.user
        try:
            skill.full_clean()  # enforce Python-level constraints
            skill.save()
            messages.success(request, 'Skill added successfully!')
            return redirect('skills')
        except ValidationError as e:
            # Handle validation errors
            if hasattr(e, 'error_dict'):
                for field, errors in e.error_dict.items():
                    form.add_error(field, errors)
            else:
                form.add_error(None, str(e))
    
    # If form is invalid, re-render with errors
    filter_form = SkillFilterForm(user=request.user)
    skills = Skill.objects.filter(user=request.user).order_by('-created_date')
    existing_categories = list(Skill.objects.filter(user=request.user).values_list('category', flat=True).distinct())
    predefined_categories = [choice[0] for choice in Skill.SKILL_CATEGORIES]
    
    return render(request, 'skills.html', {
        'skills': skills,
        'form': form,
        'filter_form': filter_form,
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
            return redirect('skills')
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
        
        return render(request, 'skills.html', {
            'skills': skills,
            'form': form,
            'filter_form': filter_form,
            'editing_id': skill_id,
            'existing_categories': existing_categories,
            'predefined_categories': predefined_categories,
        })


@login_required
@require_http_methods(["POST"])
def delete_skill(request, skill_id):
    """Delete skill entry"""
    skill = get_object_or_404(Skill, skill_id=skill_id, user=request.user)
    skill.delete()
    messages.success(request, 'Skill deleted successfully!')
    return redirect('skills')


@login_required
def get_skill_data(request, skill_id):
    """Get skill data for editing (AJAX endpoint)"""
    skill = get_object_or_404(Skill, skill_id=skill_id, user=request.user)
    
    data = {
        'category': skill.category,
        'skill_type': skill.skill_type or '',
        'title': skill.title or '',
        'description': skill.description or '',
        'skill_level': skill.skill_level or '',
        'years_experience': skill.years_experience or '',
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