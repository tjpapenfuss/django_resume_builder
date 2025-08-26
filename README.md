# django_resume_builder

# AI-Powered Resume Builder & Job Application Tracker

A Django-based web application that helps job seekers optimize their resumes by intelligently analyzing job postings and tracking application progress.

## Core Features

### Smart Job Analysis
- Scrapes job descriptions from company URLs
- Uses AI (OpenAI GPT) to extract skills, requirements, and technologies
- Identifies required vs. preferred qualifications
- Extracts resume keywords using OpenAI's 3.5-turbo model

### Application Management
- Track job applications through multiple stages (saved, applied, interviewing, etc.)
- Dashboard with pipeline visualization and application statistics
- Status updates with real-time feedback

### Experience Management
- Store and organize work experiences with structured data
- Filter experiences by company, role, and date ranges
- Prepare targeted content for specific job applications

### AI-Enhanced Insights
- Automatically categorize skills and technologies mentioned in job postings
- Generate resume focus recommendations based on job requirements
- Identify key responsibilities and experience requirements
- Detect concerning language or unrealistic expectations in job postings

## Technical Stack

- **Backend**: Django, PostgreSQL
- **AI Integration**: OpenAI API (GPT-3.5/GPT-4)
- **Frontend**: HTML, CSS, JavaScript
- **Data Storage**: JSON fields for flexible job data, UUID primary keys
- **Web Scraping**: Custom scrapers for job posting content

## Overview

The application addresses the common challenge of tailoring resumes to specific job requirements by automating the analysis of job postings and providing data-driven insights for resume optimization.

## Installation

Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate
```

Install the requirements
```bash
pip install -r requirements.txt
```

Create and store your environment variables
```bash
# Application settings
ENVIRONMENT=development
DEBUG=true

# =====================================================
# .env.example file (create this as a template)
# Copy this to .env and fill in your actual values
# =====================================================
DB_HOST=localhost or cloud postgres db host
DB_PORT=5432
DB_NAME=database_name
DB_USERNAME=postgres
DB_PASSWORD=DB_PWD
DB_SSL_MODE=require
ENVIRONMENT=development
DEBUG=true

DJANGO_PROJECT_SECRET_KEY = 'django-insecure-******'

# This is not a mandatory field. You can use this without AI assistance. 
OPENAI_API_KEY = 'sk-proj-********'


```

Run the script
```bash
python sp500.py
```