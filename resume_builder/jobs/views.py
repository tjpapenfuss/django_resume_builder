from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from .forms import JobURLForm
from .models import JobPosting, JobApplication
from .services.job_scraper import JobDescriptionScraper
from .services.ai_analyzer import analyze_job_with_ai
from django.views.decorators.http import require_http_methods
import json
from datetime import timezone

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
                    
                    return redirect('jobs:job_detail', pk=existing_job.pk)
                
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
                
                return redirect('jobs:job_detail', pk=job_posting.pk)
                
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
def skill_gap(request, pk):
    """Detailed view of a specific job posting with skill matching analysis"""
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
    
    # Initialize skill_match_analysis as None
    skill_match_analysis = None
    
    # Add skill matching analysis if user has skills
    try:
        from skills.services.job_skill_matcher import JobSkillMatcher
        matcher = JobSkillMatcher(request.user, job)
        skill_match_analysis = matcher.analyze_match()
    except ImportError:
        # Handle case where service doesn't exist yet
        messages.warning(request, 'Skill matching service not available')
    except Exception as e:
        # Handle other errors gracefully
        messages.error(request, f'Error analyzing skills: {str(e)}')
    
    context = {
        'job': job,
        'application': application,
        'parsed_requirements': parsed_requirements,
        'scraped_content': scraped_content,
        'matching_opportunities': matching_opportunities,
        'skill_match_analysis': skill_match_analysis,  # Add the skill analysis
    }
    
    return render(request, 'jobs/skill_gap.html', context)

@login_required
def job_detail_extended(request, pk):
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
    
    return render(request, 'jobs/job_detail_extended.html', context)

@login_required
@require_http_methods(["POST"])
def update_application_status(request, pk):
    """Update application status via AJAX"""
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
        return redirect('jobs:job_list')
    
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
def job_skill_gap_simple(request, pk):
    job = get_object_or_404(JobPosting, pk=pk)
    
    try:
        from skills.services.job_skill_matcher import JobSkillMatcher
        matcher = JobSkillMatcher(request.user, job)
        skill_match_analysis = matcher.analyze_match()
    except Exception as e:
        skill_match_analysis = None
        messages.error(request, f'Error analyzing skills: {str(e)}')
    
    context = {
        'job': job,
        'skill_match_analysis': skill_match_analysis,
    }
    
    return render(request, 'jobs/skill_gap.html', context)

@login_required
@require_http_methods(["POST"])
def analyze_job_api(request, pk):
    """API endpoint to trigger AI analysis for a job"""
    try:
        job = get_object_or_404(JobPosting, pk=pk)
        
        # Check if user has access to this job
        application = JobApplication.objects.filter(
            user=request.user, 
            job_posting=job
        ).first()
        
        if not application:
            return JsonResponse({
                'success': False,
                'message': 'You do not have access to this job'
            }, status=403)
        
        # Call your AI analysis function
        ai_analysis = analyze_job_with_ai(job)
        
        if ai_analysis:
            return JsonResponse({
                'success': True,
                'message': 'Job analyzed successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'AI analysis failed'
            }, status=500)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)

@login_required
def dashboard(request):
    """Dashboard showing job application stats and skill analysis options"""
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
    
    # Check if user has data needed for skill analysis
    try:
        from experience.models import Experience
        from skills.models import SkillAnalysis
        
        experience_count = Experience.objects.filter(user=request.user).count()
        job_count = applications.count()
        can_analyze = experience_count > 0 and job_count > 0
        
        # Get latest analysis if exists
        latest_analysis = SkillAnalysis.objects.filter(user=request.user).first()
    except ImportError:
        # Handle case where models don't exist yet
        experience_count = 0
        job_count = applications.count()
        can_analyze = False
        latest_analysis = None
    
    context = {
        'stats': stats,
        'can_analyze_skills': can_analyze,
        'experience_count': experience_count,
        'job_count': job_count,
        'latest_analysis': latest_analysis,
    }
    
    return render(request, 'jobs/dashboard.html', context)

# Add this to your jobs/views.py

@login_required
def job_interview_assistant(request, pk):
    """Interview Assistant - Shows experiences that match job skills for interview prep"""
    job = get_object_or_404(JobPosting, pk=pk)
    
    # Get or create application record for this user
    application, created = JobApplication.objects.get_or_create(
        user=request.user,
        job_posting=job,
        defaults={'status': 'saved'}
    )
    
    try:
        from experience.models import Experience
        from skills.models import ExperienceSkill
        
        # Get job's required skills
        job_skills = []
        if job.ai_analysis:
            job_skills.extend(job.ai_required_skills)
            job_skills.extend(job.ai_preferred_skills)
        else:
            # Fallback to parsed requirements
            job_skills.extend(job.required_skills)
            job_skills.extend(job.preferred_skills)
        
        # Remove duplicates and clean up
        job_skills = list(set([skill.strip() for skill in job_skills if skill.strip()]))
        
        # Find user's experiences that match these skills
        matching_experiences = []
        user_experiences = Experience.objects.filter(
            user=request.user, 
            visibility='public'
        ).prefetch_related('skills', 'experienceskill_set__skill')
        
        for experience in user_experiences:
            # Get all skills for this experience
            experience_skills = experience.skills.values_list('title', flat=True)
            
            # Find matching skills (case-insensitive)
            matching_skills = []
            primary_skills = []
            
            for job_skill in job_skills:
                for exp_skill_title in experience_skills:
                    if job_skill.lower() in exp_skill_title.lower() or exp_skill_title.lower() in job_skill.lower():
                        matching_skills.append(job_skill)
                        
                        # Check if this is a primary skill for this experience
                        try:
                            exp_skill_rel = ExperienceSkill.objects.get(
                                experience=experience,
                                skill__title=exp_skill_title
                            )
                            if exp_skill_rel.prominence == 'primary':
                                primary_skills.append(job_skill)
                        except ExperienceSkill.DoesNotExist:
                            pass
                        
                        break  # Only match once per job skill
            
            # Only include experiences with at least 1 matching skill
            if matching_skills:
                matching_experiences.append({
                    'experience': experience,
                    'matching_skills': list(set(matching_skills)),  # Remove duplicates
                    'primary_skills': list(set(primary_skills)),
                    'skill_count': len(set(matching_skills)),
                })
        
        # Sort by skill count (descending), then by primary skills count
        matching_experiences.sort(
            key=lambda x: (x['skill_count'], len(x['primary_skills'])), 
            reverse=True
        )
        
        # Calculate summary stats
        total_skills_covered = len(set([
            skill for exp in matching_experiences 
            for skill in exp['matching_skills']
        ]))
        
        multi_skill_experiences = len([
            exp for exp in matching_experiences 
            if exp['skill_count'] >= 2
        ])
        
        context = {
            'job': job,
            'application': application,
            'interview_experiences': matching_experiences,
            'total_skills_covered': total_skills_covered,
            'multi_skill_experiences': multi_skill_experiences,
        }
        
    except ImportError:
        # Handle case where models don't exist
        messages.error(request, 'Experience and skills models not available')
        context = {
            'job': job,
            'application': application,
            'interview_experiences': [],
            'total_skills_covered': 0,
            'multi_skill_experiences': 0,
        }
    except Exception as e:
        # Handle other errors gracefully
        messages.error(request, f'Error loading interview data: {str(e)}')
        context = {
            'job': job,
            'application': application,
            'interview_experiences': [],
            'total_skills_covered': 0,
            'multi_skill_experiences': 0,
        }
    
    return render(request, 'jobs/interview_assistant.html', context)

# Add these imports to your jobs/views.py file
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from django.conf import settings

# Add these new view functions to your jobs/views.py file

@login_required
@require_http_methods(["POST"])
def generate_experience_prompt(request, pk):
    """Generate AI prompt for experience based on job description and skill"""
    try:
        job = get_object_or_404(JobPosting, pk=pk)
        
        # Ensure user has access to this job
        application = JobApplication.objects.filter(
            user=request.user, 
            job_posting=job
        ).first()
        
        if not application:
            return JsonResponse({
                'success': False,
                'message': 'You do not have access to this job'
            }, status=403)
        
        # Parse request data
        data = json.loads(request.body)
        skill_name = data.get('skill_name', '').strip()
        
        if not skill_name:
            return JsonResponse({
                'success': False,
                'message': 'Skill name is required'
            }, status=400)
        
        # Generate AI prompt
        from jobs.services.experience_prompt_generator import ExperiencePromptGenerator
        generator = ExperiencePromptGenerator(job, skill_name)
        prompt = generator.generate_prompt()
        
        if prompt:
            return JsonResponse({
                'success': True,
                'prompt': prompt,
                'skill_name': skill_name
            })
        else:
            # Fallback to generic prompt if AI fails
            fallback_prompt = generate_fallback_prompt(skill_name, job)
            return JsonResponse({
                'success': True,
                'prompt': fallback_prompt,
                'skill_name': skill_name
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error generating prompt: {str(e)}'
        }, status=500)


# @login_required
# @require_http_methods(["POST"])
# def quick_add_experience(request, pk):
#     """Create a quick experience entry from the modal"""
#     try:
#         job = get_object_or_404(JobPosting, pk=pk)
        
#         # Ensure user has access to this job
#         application = JobApplication.objects.filter(
#             user=request.user, 
#             job_posting=job
#         ).first()
        
#         if not application:
#             return JsonResponse({
#                 'success': False,
#                 'message': 'You do not have access to this job'
#             }, status=403)
        
#         # Get form data
#         skill_name = request.POST.get('skill_name', '').strip()
#         experience_text = request.POST.get('experience_text', '').strip()
        
#         if not skill_name or not experience_text:
#             return JsonResponse({
#                 'success': False,
#                 'message': 'Both skill name and experience text are required'
#             }, status=400)
        
#         # Validate minimum length
#         if len(experience_text.split()) < 20:
#             return JsonResponse({
#                 'success': False,
#                 'message': 'Please provide a more detailed experience (at least 20 words)'
#             }, status=400)
        
#         # Create the experience record
#         from experience.models import Experience
        
#         # Generate a title from skill name and job
#         title = f"{skill_name} - {job.company_name}"
        
#         experience = Experience.objects.create(
#             user=request.user,
#             title=title,
#             description=experience_text,
#             experience_type='professional',  # Default to professional
#             visibility='private',  # Start as private for AI processing
#             skills_used=[skill_name],
#             tags=[skill_name.lower().replace(' ', '-'), 'quick-add', job.company_name.lower().replace(' ', '-')],
#             details={
#                 'source': 'quick_add_modal',
#                 'job_posting_id': str(job.pk),
#                 'job_title': job.job_title,
#                 'company_name': job.company_name,
#                 'skill_context': skill_name,
#                 'raw_input': experience_text,
#                 'needs_ai_processing': True
#             }
#         )
        
#         # Queue for AI processing (optional - for future enhancement)
#         try:
#             from .tasks import process_quick_experience_async
#             process_quick_experience_async.delay(experience.experience_id)
#         except ImportError:
#             # If Celery isn't set up, process synchronously
#             process_quick_experience_sync(experience)
        
#         return JsonResponse({
#             'success': True,
#             'message': 'Experience added successfully',
#             'experience_id': str(experience.experience_id)
#         })
        
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'message': f'Error creating experience: {str(e)}'
#         }, status=500)


def generate_fallback_prompt(skill_name, job):
    """Generate a concise fallback prompt when AI is unavailable"""
    company_name = job.company_name
    job_title = job.job_title
    
    # Simple skill-specific action examples
    action_examples = {
        'Python': 'build APIs, automate workflows, or create data analysis scripts',
        'SQL': 'optimize queries, design database schemas, or create complex joins',
        'JavaScript': 'build interactive UIs, handle API integrations, or implement real-time features',
        'React': 'create reusable components, manage application state, or optimize performance',
        'AWS': 'architect cloud solutions, implement security protocols, or optimize costs',
        'Snowflake': 'design data models, create data flows, or leverage features like time travel',
        'Docker': 'containerize applications, orchestrate deployments, or optimize build processes',
        'Kubernetes': 'manage cluster deployments, implement scaling strategies, or configure networking',
    }
    
    # Get specific examples or use generic ones
    examples = action_examples.get(skill_name, 'implement solutions, solve complex problems, or deliver measurable results')
    
    prompt = f"""
    <p>Since you're targeting the <strong>{job_title}</strong> role at <strong>{company_name}</strong>, tell us about a specific time when you used <strong>{skill_name}</strong> professionally.</p>
    
    <p>Think about a situation where you had to {examples}. What was the challenge, and what specific actions did you take?</p>
    """
    
    return prompt

def process_quick_experience_sync(experience):
    """Process quick experience synchronously with AI enhancement"""
    try:
        # Import your existing AI services
        from experience.services.ai_analyzer import analyze_experience_with_ai
        
        # Run AI analysis on the quick experience
        ai_analysis = analyze_experience_with_ai(experience)
        
        if ai_analysis:
            # Update experience with AI insights
            details = experience.details or {}
            details['ai_analysis'] = ai_analysis
            details['ai_processed'] = True
            #details['processed_at'] = timezone.now().isoformat()
            
            # Extract additional skills if found
            detected_skills = []
            for skill_category in ['technical_skills', 'soft_skills', 'tools_and_technologies', 'domain_expertise']:
                detected_skills.extend(ai_analysis.get(skill_category, []))
            
            if detected_skills:
                # Merge with existing skills, avoiding duplicates
                current_skills = experience.skills_used or []
                all_skills = list(set(current_skills + detected_skills))
                experience.skills_used = all_skills
            
            # Generate an improved description if possible
            improved_description = generate_improved_description(experience, ai_analysis)
            if improved_description:
                details['original_description'] = experience.description
                details['ai_improved_description'] = improved_description
                # Optionally replace the description
                # experience.description = improved_description
            
            experience.details = details
            experience.save()
            
    except Exception as e:
        # Log the error but don't fail the experience creation
        print(f"Error processing quick experience with AI: {str(e)}")
        
        # Still mark as processed, even if AI failed
        details = experience.details or {}
        details['ai_processing_failed'] = True
        details['ai_error'] = str(e)
        details['processed_at'] = timezone.now().isoformat()
        experience.details = details
        experience.save()


def generate_improved_description(experience, ai_analysis):
    """Generate an improved description based on AI analysis"""
    try:
        # This is a placeholder for your AI description improvement logic
        # You might want to use your existing AI services or create a new one
        
        original_text = experience.description
        skill_context = experience.details.get('skill_context', '')
        
        # For now, return None to keep original description
        # You can implement this with your preferred AI service
        return None
        
    except Exception as e:
        print(f"Error generating improved description: {str(e)}")
        return None

