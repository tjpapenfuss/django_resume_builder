# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Education
from .forms import EducationForm

@login_required
def education(request):
    """Education management view"""
    educations = Education.objects.filter(user=request.user).order_by('-date_started', '-created_date')
    form = EducationForm()
    
    return render(request, 'education.html', {
        'educations': educations,
        'form': form
    })

@login_required
@require_http_methods(["POST"])
def add_education(request):
    """Add new education entry"""
    form = EducationForm(request.POST)
    if form.is_valid():
        education = form.save(commit=False)
        education.user = request.user
        education.save()
        messages.success(request, 'Education entry added successfully!')
        return redirect('education')
    else:
        educations = Education.objects.filter(user=request.user).order_by('-date_started', '-created_date')
        return render(request, 'education.html', {
            'educations': educations,
            'form': form
        })

@login_required
@require_http_methods(["POST"])
def update_education(request, education_id):
    """Update existing education entry"""
    education = get_object_or_404(Education, education_id=education_id, user=request.user)
    form = EducationForm(request.POST, instance=education)
    
    if form.is_valid():
        form.save()
        messages.success(request, 'Education entry updated successfully!')
        return redirect('education')
    else:
        # Return JSON response with errors for AJAX handling
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
        else:
            educations = Education.objects.filter(user=request.user).order_by('-date_started', '-created_date')
            return render(request, 'education.html', {
                'educations': educations,
                'form': form,
                'editing_id': education_id
            })

@login_required
@require_http_methods(["POST"])
def delete_education(request, education_id):
    """Delete education entry"""
    education = get_object_or_404(Education, education_id=education_id, user=request.user)
    education.delete()
    messages.success(request, 'Education entry deleted successfully!')
    return redirect('education')

@login_required
def get_education_data(request, education_id):
    """Get education data for editing (AJAX endpoint)"""
    education = get_object_or_404(Education, education_id=education_id, user=request.user)
    
    data = {
        'institution_name': education.institution_name,
        'location': education.location or '',
        'major': education.major or '',
        'minor': education.minor or '',
        'gpa': education.gpa,
        'date_started': education.date_started.strftime('%Y-%m-%d') if education.date_started else '',
        'date_finished': education.date_finished.strftime('%Y-%m-%d') if education.date_finished else '',
    }
    
    return JsonResponse(data)