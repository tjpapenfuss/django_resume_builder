from django.urls import path
from . import views
from experience.views import quick_add_experience

app_name = 'jobs'

urlpatterns = [
    # View and add jobs
    path('', views.job_list, name='job_list'),
    path('add/', views.add_job_from_url, name='add_job_from_url'),

    # Job details and skill analysis
    path('<uuid:pk>/', views.skill_gap, name='job_detail'),
    path('<uuid:pk>/extended/', views.job_detail_extended, name='job_detail_extended'),

    # Analyze job -- not currently being used
    path('api/job/<uuid:pk>/analyze/', views.analyze_job_api, name='analyze_job_api'),

    # Delete Jobs
    path('<uuid:pk>/delete/', views.job_delete, name='job_delete'),

    # Job Dashboard
    path('dashboard/', views.dashboard, name='job_dashboard'),

    path('api/<uuid:pk>/skills/', views.job_skills_api, name='job_skills_api'),
    path('api/application/<uuid:pk>/status/', views.update_application_status, name='update_application_status'),
    path('<uuid:pk>/skill-gap/', views.job_skill_gap_simple, name='job_skill_gap'),

    # Interview Assistant
    path('job/<uuid:pk>/interview-assistant/', views.job_interview_assistant, name='job_interview_assistant'),

    path('<uuid:pk>/generate-experience-prompt/', views.generate_experience_prompt, name='generate_experience_prompt'),
    path('<uuid:pk>/quick-add-experience/', quick_add_experience, name='quick_add_experience'),

    # Notes page and API endpoints
    path('<uuid:pk>/notes/', views.job_notes_page, name='job_notes_page'),
    path('api/jobs/<uuid:pk>/notes/', views.job_notes_api, name='job_notes_api'),
    path('api/notes/<uuid:note_id>/', views.note_detail_api, name='note_detail_api'),

    # Note Template API endpoints
    path('api/templates/', views.note_templates_api, name='note_templates_api'),
    path('api/templates/<uuid:template_id>/', views.note_template_detail_api, name='note_template_detail_api'),
]