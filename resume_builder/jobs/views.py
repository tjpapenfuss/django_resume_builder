
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from .forms import JobURLForm
from .models import JobPosting, JobApplication
from .services.job_scraper import JobDescriptionScraper
import json
from .services.ai_analyzer import analyze_job_with_ai

@login_required
def add_job_from_url(request):
    """Add a job by scraping from URL or manual input"""
    if request.method == 'POST':
        form = JobURLForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data['url']
            manual_description = form.cleaned_data.get('manual_description', '').strip()
            
            try:
                # Check if job already exists
                existing_job = JobPosting.objects.filter(url=url).first()
                if existing_job:
                    # If manual description provided, update the existing job
                    if manual_description:
                        scraper = JobDescriptionScraper()
                        updated_job = scraper.update_job_with_manual_input(
                            existing_job, manual_description
                        )
                        messages.success(request, f'Updated job with manual description: {updated_job.job_title}')
                    
                    # Create application record if doesn't exist
                    application, created = JobApplication.objects.get_or_create(
                        user=request.user,
                        job_posting=existing_job,
                        defaults={'status': 'saved'}
                    )
                    
                    if created:
                        messages.info(request, f'Job already exists. Added to your saved jobs: {existing_job.job_title}')
                    else:
                        messages.info(request, f'You already have this job saved: {existing_job.job_title}')
                    
                    return redirect('job_detail', pk=existing_job.pk)
                
                # Create new job
                scraper = JobDescriptionScraper()
                
                if manual_description:
                    # Use manual description
                    job_posting = scraper.create_job_from_manual_input(
                        url=url,
                        manual_text=manual_description,
                        user=request.user
                    )
                    messages.success(request, f'Successfully created job from manual input: {job_posting.job_title} at {job_posting.company_name}')
                else:
                    # Use auto-scraping
                    job_posting = scraper.scrape_job_from_url(url, request.user)
                    messages.success(request, f'Successfully scraped job: {job_posting.job_title} at {job_posting.company_name}')
                
                # Create application record for user
                JobApplication.objects.create(
                    user=request.user,
                    job_posting=job_posting,
                    status='saved'
                )
                
                return redirect('job_detail', pk=job_posting.pk)
                
            except Exception as e:
                messages.error(request, f'Failed to process job: {str(e)}')
    else:
        form = JobURLForm()
    
    return render(request, 'jobs/add_from_url.html', {'form': form})

@login_required
def job_list(request):
    """List all jobs saved by the user"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    # Get user's job applications
    applications = JobApplication.objects.filter(user=request.user).select_related('job_posting')
    
    # Apply filters
    if search_query:
        applications = applications.filter(
            Q(job_posting__job_title__icontains=search_query) |
            Q(job_posting__company_name__icontains=search_query)
        )
    
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(applications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': JobApplication.STATUS_CHOICES
    }
    
    return render(request, 'jobs/list.html', context)

@login_required
def job_detail(request, pk):
    """Detailed view of a specific job posting"""
    job = get_object_or_404(JobPosting, pk=pk)
    
    # Get or create application record for this user
    application, created = JobApplication.objects.get_or_create(
        user=request.user,
        job_posting=job,
        defaults={'status': 'saved'}
    )
    
    # Extract data from JSON for display
    json_data = job.raw_json
    scraped_content = json_data.get('scraped_content', {})
    parsed_requirements = json_data.get('parsed_requirements', {})
    matching_opportunities = json_data.get('matching_opportunities', {})
    context = {
        'job': job,
        'application': application,
        'parsed_requirements': job.raw_json.get('parsed_requirements', {}),
        'scraped_content': job.raw_json.get('scraped_content', {}),
        # AI analysis is accessed via job.ai_analysis property
        'matching_opportunities': matching_opportunities,
    }
    
    return render(request, 'jobs/detail.html', context)

@login_required
def update_application_status(request, pk):
    """Update application status via AJAX"""
    if request.method == 'POST':
        application = get_object_or_404(JobApplication, pk=pk, user=request.user)
        new_status = request.POST.get('status')
        
        if new_status in dict(JobApplication.STATUS_CHOICES):
            application.status = new_status
            application.save()
            
            return JsonResponse({
                'success': True,
                'new_status': application.get_status_display()
            })
    
    return JsonResponse({'success': False})

@login_required
def job_delete(request, pk):
    """Delete a job application"""
    application = get_object_or_404(JobApplication, job_posting__pk=pk, user=request.user)
    
    if request.method == 'POST':
        job_title = application.job_posting.job_title
        application.delete()
        messages.success(request, f'Removed "{job_title}" from your saved jobs.')
        return redirect('job_list')
    
    return render(request, 'jobs/confirm_delete.html', {'application': application})

@login_required
def job_skills_api(request, pk):
    """API endpoint to get job skills for matching"""
    job = get_object_or_404(JobPosting, pk=pk)
    
    data = {
        'required_skills': job.required_skills,
        'preferred_skills': job.preferred_skills,
        'all_skills': job.all_skills,
        'experience_requirements': job.experience_requirements,
        'key_requirements': job.key_requirements
    }
    
    return JsonResponse(data)

@login_required
def dashboard(request):
    """Dashboard showing job application stats"""
    # Filter out applications with missing jobs
    applications = JobApplication.objects.filter(
        user=request.user,
        job_posting__isnull=False  
    ).select_related('job_posting')  
    
    stats = {
        'total_saved': applications.filter(status='saved').count(),  
        'applied': applications.filter(status='applied').count(),
        'interviewing': applications.filter(status__in=['phone_screen', 'interview']).count(),
        'recent_jobs': applications.order_by('-created_at')[:5]
    }
    
    return render(request, 'jobs/dashboard.html', {'stats': stats})

# Usage in your views:
def job_detail(request, pk):
    job = get_object_or_404(JobPosting, pk=pk)
    application = get_object_or_404(JobApplication, user=request.user, job_posting=job)

    # Get or create AI analysis
    ai_analysis = analyze_job_with_ai(job)
    
    context = {
        'job': job,
        'application': application,
        'parsed_requirements': job.raw_json.get('parsed_requirements', {}),
        'ai_analysis': ai_analysis,  # Add this to your context
        'scraped_content': job.raw_json.get('scraped_content', {}),
    }
    
    return render(request, 'jobs/detail.html', context)