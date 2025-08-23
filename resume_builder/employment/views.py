# views.py - Add these to your existing views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Employment
from .forms import EmploymentForm

@login_required
def employment(request):
    """Employment management view"""
    employments = Employment.objects.filter(user=request.user).order_by('-date_started', '-created_date')
    form = EmploymentForm()
    
    return render(request, 'employment.html', {
        'employments': employments,
        'form': form
    })

@login_required
@require_http_methods(["POST"])
def add_employment(request):
    """Add new employment entry"""
    form = EmploymentForm(request.POST)
    if form.is_valid():
        employment = form.save(commit=False)
        employment.user = request.user
        employment.save()
        messages.success(request, 'Employment entry added successfully!')
        return redirect('employment')
    else:
        employments = Employment.objects.filter(user=request.user).order_by('-date_started', '-created_date')
        return render(request, 'employment.html', {
            'employments': employments,
            'form': form
        })

@login_required
@require_http_methods(["POST"])
def update_employment(request, employment_id):
    """Update existing employment entry"""
    employment = get_object_or_404(Employment, employment_id=employment_id, user=request.user)
    form = EmploymentForm(request.POST, instance=employment)
    
    if form.is_valid():
        form.save()
        messages.success(request, 'Employment entry updated successfully!')
        return redirect('employment')
    else:
        # Return JSON response with errors for AJAX handling
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
        else:
            employments = Employment.objects.filter(user=request.user).order_by('-date_started', '-created_date')
            return render(request, 'employment.html', {
                'employments': employments,
                'form': form,
                'editing_id': employment_id
            })

@login_required
@require_http_methods(["POST"])
def delete_employment(request, employment_id):
    """Delete employment entry"""
    employment = get_object_or_404(Employment, employment_id=employment_id, user=request.user)
    employment.delete()
    messages.success(request, 'Employment entry deleted successfully!')
    return redirect('employment')

@login_required
def get_employment_data(request, employment_id):
    """Get employment data for editing (AJAX endpoint)"""
    employment = get_object_or_404(Employment, employment_id=employment_id, user=request.user)
    
    data = {
        'company_name': employment.company_name,
        'location': employment.location or '',
        'title': employment.title or '',
        'description': employment.description or '',
        'date_started': employment.date_started.strftime('%Y-%m-%d') if employment.date_started else '',
        'date_finished': employment.date_finished.strftime('%Y-%m-%d') if employment.date_finished else '',
    }
    
    # Add details data
    if employment.details:
        data.update({
            'responsibilities': '\n'.join(employment.details.get('responsibilities', [])),
            'achievements': '\n'.join(employment.details.get('achievements', [])),
            'skills_used': '\n'.join(employment.details.get('skills_used', [])),
            'salary': employment.details.get('salary', ''),
            'employment_type': employment.details.get('employment_type', ''),
            'supervisor': employment.details.get('supervisor', ''),
            'reason_for_leaving': employment.details.get('reason_for_leaving', ''),
        })
    
    return JsonResponse(data)