from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
import json
from .models import Experience
from jobs.models import JobPosting, JobApplication
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

    # Start with all experiences for the logged-in user, including linked skills
    experiences = Experience.objects.filter(user=request.user).prefetch_related(
        'experienceskill_set__skill'
    )

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
    # Initialize variables used in context
    suggested_skill = request.GET.get('skill', '')
    conversation_id = request.GET.get('conversation_id', '')
    conversation_data = None
    
    if request.method == 'POST':
        # Handle form submission (existing code)
        form = ExperienceForm(request.POST, user=request.user)
        if form.is_valid():
            print("Found form")
            experience = form.save(commit=False)
            experience.user = request.user  # attach user to entry
            
            # Link to conversation if conversation_id is provided
            conversation_id = request.POST.get('conversation_id', '')
            existing_experience = None

            if conversation_id:
                try:
                    from conversation.models import Conversation
                    conversation = Conversation.objects.get(
                        conversation_id=conversation_id,
                        user=request.user
                    )

                    # Check if this conversation already has an experience
                    existing_experience = conversation.experiences.first()

                    if existing_experience:
                        # Update existing experience instead of creating new one
                        # Always use the form data (which includes the latest conversation summary from GET pre-fill)
                        existing_experience.description = experience.description

                        existing_experience.title = experience.title
                        existing_experience.experience_type = experience.experience_type
                        existing_experience.employment = experience.employment
                        existing_experience.education = experience.education
                        existing_experience.date_started = experience.date_started
                        existing_experience.date_finished = experience.date_finished
                        existing_experience.visibility = experience.visibility
                        existing_experience.save()
                        experience = existing_experience  # Use the updated experience

                        # Mark conversation as resumable for future iterations
                        from conversation.services.conversation_manager import ConversationManager
                        ConversationManager.complete_conversation_with_experience(
                            str(conversation.conversation_id),
                            experience.description
                        )

                        messages.success(request, 'Experience updated with additional context from your conversation!')
                    else:
                        # Create new experience and link to conversation
                        experience.conversation = conversation
                        experience.save()

                        # Mark conversation as resumable for future iterations
                        from conversation.services.conversation_manager import ConversationManager
                        ConversationManager.complete_conversation_with_experience(
                            str(conversation.conversation_id),
                            experience.description
                        )

                        messages.success(request, 'Experience created from your conversation!')

                except Conversation.DoesNotExist:
                    # If conversation doesn't exist or doesn't belong to user, ignore
                    experience.save()
            else:
                experience.save()
            print("found the saving. ")
            
            # Always run AI analysis and redirect to skill confirmation page
            return redirect('experience:analyze_experience_skills', experience_id=experience.experience_id)
        else:
            print('Form is not valid. ')
    else:
        # Pre-populate from URL parameters
        initial_data = {}
        
        # Note: suggested_skill is kept for context but no longer auto-fills form fields
        
        # If conversation_id is provided, try to get conversation data for auto-filling
        if conversation_id:
            try:
                from conversation.models import Conversation
                conversation = Conversation.objects.get(
                    conversation_id=conversation_id,
                    user=request.user,
                    status__in=['completed', 'resumable']  # Use completed or resumable conversations
                )

                # Check if conversation already has an experience - if so, pre-fill with that data
                existing_experience = conversation.experiences.first()
                if existing_experience:
                    # For resumed conversations, use the latest conversation summary for description
                    # but keep other fields from existing experience
                    description_to_use = existing_experience.description

                    # If conversation has been updated (resumable status), use latest summary
                    if conversation.status == 'resumable' and conversation.experience_summary:
                        import json
                        try:
                            summary_data = json.loads(conversation.experience_summary)
                            description_to_use = summary_data.get('narrative_summary', conversation.experience_summary)
                        except json.JSONDecodeError:
                            description_to_use = conversation.experience_summary

                    # Pre-fill form with existing experience data but updated description
                    initial_data = {
                        'title': existing_experience.title,
                        'description': description_to_use,
                        'experience_type': existing_experience.experience_type,
                        'employment': existing_experience.employment,
                        'education': existing_experience.education,
                        'date_started': existing_experience.date_started,
                        'date_finished': existing_experience.date_finished,
                        'visibility': existing_experience.visibility,
                    }
                    conversation_data = {
                        'title': existing_experience.title,
                        'summary': {'narrative_summary': description_to_use}
                    }
                elif conversation.experience_summary:
                    # Try to parse the summary if it's JSON
                    import json
                    try:
                        summary_data = json.loads(conversation.experience_summary)
                        conversation_data = {
                            'title': conversation.title or summary_data.get('role_context', ''),
                            'summary': summary_data
                        }
                        
                        # Auto-fill form fields from conversation data
                        initial_data['title'] = conversation.title or summary_data.get('role_context', '')
                        initial_data['description'] = summary_data.get('narrative_summary', '')
                        
                    except json.JSONDecodeError:
                        # If it's not JSON, use as plain text
                        conversation_data = {
                            'title': conversation.title or 'Experience from Conversation',
                            'summary': {'narrative_summary': conversation.experience_summary}
                        }
                        initial_data['title'] = conversation.title or 'Experience from Conversation'
                        initial_data['description'] = conversation.experience_summary
                        
            except Conversation.DoesNotExist:
                # Conversation doesn't exist or doesn't belong to user
                pass
        
        form = ExperienceForm(initial=initial_data, user=request.user)
    
    context = {
        'form': form,
        'suggested_skill': suggested_skill,
        'from_skill_analysis': bool(suggested_skill),
        'conversation_id': conversation_id,
        'from_conversation': bool(conversation_id),
        'conversation_data': conversation_data,
    }
    
    return render(request, 'add_experience.html', context)
@login_required
@require_http_methods(["POST"])
def quick_add_experience(request, pk):
    """Create a quick experience entry from the modal with skill linking"""
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
        # Get form data
        skill_name = request.POST.get('skill_name', '').strip()
        experience_text = request.POST.get('experience_text', '').strip()
        
        if not skill_name or not experience_text:
            return JsonResponse({
                'success': False,
                'message': 'Both skill name and experience text are required'
            }, status=400)
        # Validate minimum length
        if len(experience_text.split()) < 20:
            return JsonResponse({
                'success': False,
                'message': 'Please provide a more detailed experience (at least 20 words)'
            }, status=400)
        
        # Create the experience record
        from experience.models import Experience
        # Generate a title from skill name and job
        title = f"{skill_name} Experience - {job.company_name}"
        
        experience = Experience.objects.create(
            user=request.user,
            title=title,
            description=experience_text,
            experience_type='professional',
            visibility='public',  
            skills_used=[skill_name],  # Initial skill list
            tags=[
                skill_name.lower().replace(' ', '-'), 
                'quick-add', 
                job.company_name.lower().replace(' ', '-'),
                'job-targeted'
            ],
            details={
                'source': 'quick_add_modal',
                'job_posting_id': str(job.pk),
                'job_title': job.job_title,
                'company_name': job.company_name,
                'skill_context': skill_name,
                'raw_input': experience_text,
                'needs_ai_processing': True,
                'created_via_skill_gap_analysis': True
            }
        )
        
        # Create or get the skill object and link it
        skill_obj = create_or_get_skill(request.user, skill_name)
        
        # Link the primary skill to the experience
        experience_skill, created = experience.add_skill(
            skill=skill_obj,
            prominence='primary',
            proficiency=None,
            usage_notes=f'Experience created for {job.job_title} at {job.company_name}',
            method='quick_add'
        )
        
        # Create job-experience relationship
        from jobs.models import JobExperience
        
        job_experience = JobExperience.objects.create(
            job_posting=job,
            experience=experience,
            user=request.user,
            relevance='created_for',
            target_skills=[skill_name],
            creation_source='quick_add',
            relevance_notes=f'Experience created specifically to demonstrate {skill_name} for this position'
        )
        
        # Always run AI analysis to detect additional skills (like regular add experience form)
        # This will redirect the frontend to the skill analysis page
        return JsonResponse({
            'success': True,
            'redirect_to_analysis': True,  # Signal frontend to redirect
            'analysis_url': f'/experience/analyze/{experience.experience_id}',
            'experience_id': str(experience.experience_id),
            'skill_linked': skill_obj.title,
            'job_linked': job.job_title,
            'message': 'Experience created! Now analyzing for additional skills...'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating experience: {str(e)}'
        }, status=500)


def create_or_get_skill(user, skill_name):
    """Create or retrieve a skill object for the user"""
    from skills.models import Skill
    
    # Try to find existing skill (case-insensitive)
    existing_skill = Skill.objects.filter(
        user=user,
        title__iexact=skill_name
    ).first()
    
    if existing_skill:
        return existing_skill
    
    # Create new skill
    skill_type, skill_category = determine_skill_classification(skill_name)
    skill = Skill.objects.create(
        user=user,
        title=skill_name,
        category=skill_category,
        skill_type=skill_type,
        description=f'Skill extracted from experience targeting {skill_name}',
        details={
            'source': 'quick_add_modal',
            'auto_created': True,
            'needs_user_review': True
        }
    )
    return skill


def determine_skill_classification(skill_name):
    """Determine skill type and category based on skill name"""
    skill_lower = skill_name.lower()
    
    # Technical skills
    technical_keywords = [
        'python', 'java', 'javascript', 'sql', 'react', 'angular', 'vue',
        'aws', 'azure', 'docker', 'kubernetes', 'git', 'api', 'rest',
        'snowflake', 'tableau', 'power bi', 'excel', 'r', 'matlab',
        'machine learning', 'ai', 'data science', 'blockchain', 'html',
        'css', 'node', 'express', 'mongodb', 'postgresql', 'redis'
    ]
    
    # Soft skills
    soft_skills_keywords = [
        'leadership', 'communication', 'teamwork', 'problem solving',
        'critical thinking', 'time management', 'project management',
        'collaboration', 'presentation', 'negotiation', 'mentoring',
        'public speaking', 'writing', 'research', 'analytical thinking'
    ]
    
    if any(keyword in skill_lower for keyword in technical_keywords):
        return 'Technical', 'Technology'
    elif any(keyword in skill_lower for keyword in soft_skills_keywords):
        return 'Soft', 'Communication' if 'communication' in skill_lower else 'Leadership'
    else:
        return 'Hard', 'Other'


def process_quick_experience_with_skill_linking(experience, primary_skill_name, job):
    """Enhanced processing that includes skill linking"""
    try:
        from experience.services.ai_analyzer import analyze_experience_with_ai
        
        # Run AI analysis
        ai_analysis = analyze_experience_with_ai(experience)
        
        if ai_analysis:
            # Update experience details
            details = experience.details or {}
            details['ai_analysis'] = ai_analysis
            details['ai_processed'] = True
            #details['processed_at'] = timezone.now().isoformat()
            
            # Extract all detected skills
            all_detected_skills = []
            for skill_category in ['technical_skills', 'soft_skills', 'tools_and_technologies', 'domain_expertise']:
                all_detected_skills.extend(ai_analysis.get(skill_category, []))
            
            # Link additional skills found by AI
            skills_linked = []
            for skill_name in all_detected_skills:
                if skill_name.lower() != primary_skill_name.lower():  # Don't duplicate primary skill
                    skill_obj = create_or_get_skill(experience.user, skill_name)
                    
                    # Determine prominence based on skill type and relevance
                    prominence = 'secondary' if skill_name in ai_analysis.get('technical_skills', []) else 'supporting'
                    
                    exp_skill, created = experience.add_skill(
                        skill=skill_obj,
                        prominence=prominence,
                        usage_notes=f'Detected by AI analysis for {job.job_title}',
                        method='ai_suggested'
                    )
                    
                    if created:
                        skills_linked.append(skill_name)
            
            # Update job-experience link with additional skills
            try:
                from .models import JobExperience
                job_exp = JobExperience.objects.get(
                    job_posting=job,
                    experience=experience
                )
                
                # Add detected skills to target skills
                current_skills = job_exp.target_skills or []
                all_skills = list(set(current_skills + skills_linked))
                job_exp.target_skills = all_skills
                job_exp.match_score = job_exp.calculate_match_score()
                job_exp.save()
                
            except JobExperience.DoesNotExist:
                pass
            
            # Update experience skills list
            current_skills = experience.skills_used or []
            all_skills = list(set(current_skills + all_detected_skills))
            experience.skills_used = all_skills
            
            experience.details = details
            experience.save()
            
            return {
                'success': True,
                'primary_skill': primary_skill_name,
                'additional_skills': skills_linked,
                'total_skills_linked': len(skills_linked) + 1
            }
            
    except Exception as e:
        # Log error but don't fail the experience creation
        print(f"Error in AI processing: {str(e)}")
        return {'success': False, 'error': str(e)}
# Update your analyze_experience_skills view in experience/views.py

@login_required
def analyze_experience_skills(request, experience_id):
    """AI analyze experience and let user confirm/modify skills to link"""
    experience = get_object_or_404(Experience, experience_id=experience_id, user=request.user)

    if request.method == 'POST':
        # Determine where to redirect after processing
        redirect_url = determine_redirect_after_analysis(experience)
        
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
            return redirect(redirect_url)
            
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
            return redirect(redirect_url)
            
        elif action == 'skip':
            # Skip AI analysis
            messages.info(request, 'Experience saved without AI skill analysis.')
            return redirect(redirect_url)
    
    # GET request or initial load - run AI analysis
    ai_analysis = analyze_experience_with_ai(experience)
    if not ai_analysis:
        messages.error(request, 'Unable to analyze experience with AI. Please try again later.')
        return redirect(determine_redirect_after_analysis(experience))
    
    # Prepare skills data for template
    skills_data = prepare_skills_for_template(ai_analysis)

    # Get conversation data if this experience came from a conversation
    conversation = None
    if experience.conversation:
        conversation = experience.conversation

    context = {
        'experience': experience,
        'ai_analysis': ai_analysis,
        'skills_data': skills_data,
        'total_skills': sum(len(skills) for skills in skills_data.values()) if skills_data else 0,
        'from_quick_add': experience.was_quick_added,  # Add this to template context
        'target_job_info': experience.target_job_info,  # Add job info for context
        'conversation': conversation,  # Add conversation data for resume button
    }
    
    return render(request, 'analyze_skills.html', context)


def determine_redirect_after_analysis(experience):
    """Determine where to redirect user after skill analysis based on experience source"""
    
    # Check if this experience was created via quick add modal
    if experience.was_quick_added:
        job_info = experience.target_job_info
        if job_info and job_info.get('job_id'):
            # Redirect back to the skill gap analysis page for that job
            try:
                from jobs.models import JobPosting
                job = JobPosting.objects.get(pk=job_info['job_id'])
                return f'/jobs/{job.pk}/skill-gap/'  # Adjust URL pattern as needed
            except JobPosting.DoesNotExist:
                pass
    
    # Default: redirect to experiences list
    return 'experience:experience'


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
            experiences = Experience.objects.filter(user=request.user).prefetch_related('experienceskill_set__skill').order_by('-date_started', '-created_date')
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