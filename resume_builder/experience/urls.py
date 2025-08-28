from django.urls import path
from . import views

app_name = 'experience'

urlpatterns = [
    # ... your existing URLs ...
    
    # Main experiences page
    path('', views.experiences, name='experience'),
    
    # Add new experience
    path('add/', views.add_experience, name='add_experience'),

    # Update/edit/delete experience
    path('update/<uuid:experience_id>/', views.update_experience, name='update_experience'),
    path('delete/<uuid:experience_id>/', views.delete_experience, name='delete_experience'),
    
    # Get experience data (AJAX)
    path('data/<uuid:experience_id>/', views.get_experience_data, name='get_experience_data'),

    # AI skill analysis for experience
    path('analyze/<uuid:experience_id>/', views.analyze_experience_skills, name='analyze_experience_skills'),

    # # Analytics
    # path('analytics/', views.experience_analytics, name='experience_analytics'),
    
    # # API endpoints
    # path('api/resume/', views.get_experiences_for_resume, name='api_experiences_for_resume'),
]