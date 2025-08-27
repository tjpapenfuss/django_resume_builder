from django.urls import path
from . import views

app_name = 'skills'

urlpatterns = [
    # Main skills page
    path('', views.skills, name='skills'),
    
    # CRUD operations
    path('add/', views.add_skill, name='add_skill'),
    path('update/<uuid:skill_id>/', views.update_skill, name='update_skill'),
    path('delete/<uuid:skill_id>/', views.delete_skill, name='delete_skill'),
    
    # AJAX endpoints
    path('api/get-skill/<uuid:skill_id>/', views.get_skill_data, name='get_skill_data'),
    path('api/categories/', views.get_user_categories, name='get_user_categories'),
    path('api/experiences/', views.get_user_experiences, name='get_user_experiences'),
    
    # Skill Analysis URLs
    path('api/analyze/', views.run_skill_analysis, name='run_skill_analysis'),
    path('analysis/<uuid:analysis_id>/', views.skill_analysis_detail, name='skill_analysis_detail'),
    path('analysis/history/', views.skill_analysis_history, name='skill_analysis_history'),
    
    # Experience linking
    path('<uuid:skill_id>/add-experience/', views.add_experience_for_skill, name='add_experience_for_skill'),
    path('<uuid:skill_id>/link-experience/', views.link_experience_to_skill, name='link_experience_to_skill'),
]    