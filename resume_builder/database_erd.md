# Django Interview Assistant - Database ERD

```mermaid
erDiagram
    users {
        string user_id PK
        string email
        string first_name
        string last_name
        int login_count
        datetime last_login
        datetime created_date
        boolean terms_accepted
        boolean is_active
        boolean is_staff
    }

    user_token {
        string token PK
        string user_id FK
        datetime created_at
        datetime expires_at
    }

    employment {
        string employment_id PK
        string user_id FK
        string company_name
        string location
        string title
        string description
        string details
        datetime date_started
        datetime date_finished
        datetime created_date
        datetime updated_date
    }

    education {
        string education_id PK
        string user_id FK
        string institution_name
        string location
        string major
        string minor
        float gpa
        string details
        datetime date_started
        datetime date_finished
        datetime created_date
        datetime updated_date
    }

    experience {
        string experience_id PK
        string user_id FK
        string employment_id FK
        string education_id FK
        string conversation_id FK
        string title
        string description
        string experience_type
        date date_started
        date date_finished
        string skills_used
        string tags
        string details
        string visibility
        datetime created_date
        datetime modified_date
    }

    skill {
        string skill_id PK
        string user_id FK
        string category
        string title
        string description
        int years_experience
        string details
        string skill_type
        string skill_level
        datetime created_date
        datetime updated_date
    }

    experience_skill {
        string experience_skill_id PK
        string experience_id FK
        string skill_id FK
        string proficiency_demonstrated
        string prominence
        string usage_notes
        datetime created_date
        string extraction_method
    }

    job_posting {
        string job_posting_id PK
        string added_by_user_id FK
        string url
        string company_name
        string job_title
        string location
        boolean remote_ok
        datetime scraped_at
        datetime updated_at
        boolean scraping_success
        string scraping_error
        string raw_json
    }

    job_application {
        string job_application_id PK
        string user_id FK
        string job_posting_id FK
        string status
        date applied_date
        string notes
        string resume_version_used
        datetime created_at
        datetime updated_at
    }

    job_experience {
        string job_experience_id PK
        string job_posting_id FK
        string experience_id FK
        string user_id FK
        string relevance
        string target_skills
        float match_score
        datetime created_date
        string creation_source
        string relevance_notes
    }

    conversation {
        string conversation_id PK
        string user_id FK
        string status
        string title
        string experience_summary
        datetime created_at
        datetime updated_at
    }

    conversation_message {
        string message_id PK
        string conversation_id FK
        string role
        string content
        string metadata
        datetime timestamp
    }

    skill_analysis {
        string analysis_id PK
        string user_id FK
        datetime created_at
        int total_experiences_analyzed
        int total_jobs_analyzed
        int total_skills_found
        int new_skills_created
        int total_skill_gaps
        float average_job_match_score
        float highest_job_match_score
        float lowest_job_match_score
        string skill_gaps
        string job_matches
        string skills_extracted
        string analyzer_version
        string analysis_parameters
        string user_notes
        string status
    }

    users ||--o{ user_token : "has"
    users ||--o{ employment : "has"
    users ||--o{ education : "has"
    users ||--o{ experience : "owns"
    users ||--o{ skill : "owns"
    users ||--o{ job_posting : "adds"
    users ||--o{ job_application : "applies"
    users ||--o{ conversation : "has"
    users ||--o{ skill_analysis : "has"

    employment ||--o{ experience : "contextualizes"
    education ||--o{ experience : "contextualizes"
    conversation ||--o{ experience : "generates"
    conversation ||--o{ conversation_message : "contains"

    experience ||--o{ experience_skill : "demonstrates"
    skill ||--o{ experience_skill : "links"

    job_posting ||--o{ job_application : "receives"
    job_posting ||--o{ job_experience : "links"
    experience ||--o{ job_experience : "linked_to"
```

## Key Database Design Patterns

### 1. **UUID Primary Keys**
- All main models use UUID primary keys for global uniqueness
- Prevents ID guessing and supports distributed systems
- Example: `user_id`, `experience_id`, `job_posting_id`

### 2. **User-Scoped Data**
- All user data is isolated via foreign key relationships to `users`
- Ensures data privacy and supports multi-tenant architecture
- All queries should filter by `user_id` for security

### 3. **Flexible JSON Storage**
- `raw_json` in JobPosting stores scraped job data and AI analysis
- `details` fields store flexible metadata without schema changes
- `skills_used`, `tags` arrays in Experience for dynamic categorization
- `target_skills`, `skill_gaps` for job matching analysis

### 4. **Many-to-Many Through Models**
- `experience_skill`: Links experiences to skills with additional context
- `job_experience`: Links experiences to jobs with relevance scoring
- Allows storing relationship-specific metadata

### 5. **Optional Context Relationships**
- Experience can optionally link to Employment or Education
- Supports both structured (job-based) and standalone experiences
- `conversation_id` tracks AI-generated experiences

### 6. **Job Application Pipeline**
- `job_application.status` tracks application progress
- `job_experience` links relevant experiences to specific jobs
- `match_score` quantifies experience-job fit

### 7. **AI Integration Architecture**
- Conversation system for interactive experience extraction
- Skill analysis with cached results and progress tracking
- JSON fields store AI analysis results to avoid re-processing

### 8. **Performance Optimizations**
- Composite indexes on frequently queried fields
- `db_index=True` on searchable fields (company_name, job_title)
- Optimized for user-scoped filtering patterns

## Critical Relationships

1. **Experience ← → Skills**: Many-to-many through ExperienceSkill
2. **Experience ← → Jobs**: Many-to-many through JobExperience  
3. **User → Everything**: One-to-many ownership pattern
4. **Employment/Education → Experience**: Optional context relationships
5. **Conversation → Experience**: AI generation tracking
6. **JobPosting → JobApplication**: Application tracking