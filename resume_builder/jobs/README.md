# Jobs App

The Jobs app is a comprehensive job application tracking and analysis system for the Django Interview Assistant project. It provides tools for scraping job postings, analyzing skill requirements, tracking application status, and preparing for interviews.

## Features

### Job Management
- **Web Scraping**: Automatically scrape job postings from various ATS platforms (Greenhouse, Lever, Workday)
- **Manual Input**: Add job descriptions manually when scraping fails
- **Job Storage**: Store job data in structured format with JSON fields for flexibility
- **Application Tracking**: Track application status from saved to offer/rejection

### AI-Powered Analysis
- **Job Analysis**: Extract required/preferred skills, technologies, and experience requirements
- **Skill Gap Analysis**: Compare job requirements against user's experience and skills
- **Interview Preparation**: Find relevant experiences that match job requirements
- **Experience Prompts**: Generate AI prompts to help users create targeted experiences

### Note Taking
- **Job Notes**: Create categorized notes for each job (interview notes, research, follow-up)
- **Note Templates**: Reusable templates for common note types
- **Rich Text Editing**: Support for formatted note content

## Models

### JobPosting
Core model for storing job information:
- **Basic Fields**: URL, company name, job title, location, remote work flag
- **JSON Storage**: Flexible `raw_json` field for scraped content and AI analysis
- **User Tracking**: Links jobs to users who saved them
- **AI Analysis**: Cached AI-powered job analysis results

### JobApplication
Tracks user's application status:
- **Status Tracking**: From 'saved' through 'applied' to 'offer'/'rejected'
- **Metadata**: Applied date, notes, resume version used
- **User-Job Relationship**: Links users to their saved/applied jobs

### JobExperience
Links user experiences to specific jobs:
- **Relevance Tracking**: How experiences relate to job requirements
- **Skill Targeting**: Which skills each experience demonstrates for the job
- **Match Scoring**: Calculated relevance scores
- **Creation Source**: Track how the link was established (manual, AI, quick-add)

### Note & NoteTemplate
Note-taking system for job applications:
- **Categorized Notes**: Interview notes, prep, research, follow-up
- **Job Association**: Link notes to specific jobs or keep as general
- **Templates**: Reusable note structures for common scenarios

## Key Services

### JobDescriptionScraper (`services/job_scraper.py`)
Handles web scraping from job posting URLs:
- **Multi-Platform Support**: Adapters for major ATS platforms
- **Content Extraction**: Parse job titles, descriptions, requirements
- **Fallback Handling**: Manual input when scraping fails
- **Skill Detection**: Basic skill pattern matching

### AI Analyzer (`services/ai_analyzer.py`)
Provides AI-powered job analysis:
- **OpenAI Integration**: Uses GPT models for job analysis
- **Structured Output**: Extracts skills, requirements, and insights
- **Caching**: Stores results in job's JSON field
- **Error Handling**: Graceful fallbacks when AI unavailable

### Experience Prompt Generator (`services/experience_prompt_generator.py`)
Generates targeted prompts for experience creation:
- **Context-Aware**: Considers job requirements and target skills
- **Interview Focus**: Helps users prepare relevant examples
- **Fallback Prompts**: Generic prompts when AI unavailable

## Views and URLs

### Main Views
- **Dashboard** (`/jobs/dashboard/`): Overview of application stats and analysis options
- **Job List** (`/jobs/`): Paginated list of user's saved jobs with search/filter
- **Add Job** (`/jobs/add/`): Add jobs via URL scraping or manual input
- **Job Detail** (`/jobs/<pk>/`): Detailed job view with skill gap analysis
- **Interview Assistant** (`/jobs/job/<pk>/interview-assistant/`): Match experiences to job skills

### API Endpoints
- **Job Analysis** (`/jobs/api/job/<pk>/analyze/`): Trigger AI analysis
- **Status Updates** (`/jobs/api/application/<pk>/status/`): Update application status
- **Experience Prompts** (`/jobs/<pk>/generate-experience-prompt/`): Generate AI prompts
- **Notes API** (`/jobs/api/jobs/<pk>/notes/`): CRUD operations for notes
- **Templates API** (`/jobs/api/templates/`): Manage note templates

## Templates

### Core Templates
- **`dashboard.html`**: Job application overview and statistics
- **`list.html`**: Paginated job listing with search and filters
- **`add_from_url.html`**: Form for adding jobs via URL or manual input
- **`job_detail_extended.html`**: Comprehensive job details view
- **`skill_gap.html`**: Skill matching and gap analysis
- **`interview_assistant.html`**: Experience-to-skill matching for interviews
- **`notes.html`**: Note-taking interface for jobs
- **`confirm_delete.html`**: Job deletion confirmation

## Integration Points

### Experience App
- Links job requirements to user experiences
- Quick-add experiences from job skill gaps
- Experience relevance scoring

### Skills App
- Skill matching between jobs and user profiles
- Gap analysis and recommendations
- Skill-based experience filtering

### User Authentication
- All views require login
- User-scoped data access
- Permission checks for job access

## Configuration

### Required Settings
```python
# OpenAI API for job analysis
OPENAI_API_KEY = 'your-openai-api-key'

# Database configuration for JSON fields
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',  # JSON field support
        # ... other settings
    }
}
```

### Optional Features
- **Celery**: For asynchronous job processing
- **Redis**: For caching AI results
- **S3**: For storing scraped content files

## Usage Workflow

1. **Add Jobs**: Users add jobs via URL scraping or manual input
2. **AI Analysis**: System analyzes job requirements and skills
3. **Skill Matching**: Compare job needs against user's experience
4. **Experience Creation**: Generate targeted experiences for skill gaps
5. **Interview Prep**: Find relevant experiences for interview questions
6. **Application Tracking**: Update status as applications progress
7. **Note Taking**: Document research, interviews, and follow-ups

## Future Enhancements

- **Company Research**: Automatic company information gathering
- **Salary Analysis**: Market rate comparisons
- **Application Automation**: Integration with job boards
- **Interview Scheduling**: Calendar integration
- **Follow-up Reminders**: Automated application tracking
- **Analytics Dashboard**: Application success metrics