from django.urls import path
from . import views

urlpatterns = [
    # ... your existing URLs ...
    
    # skill URLs
    path('', views.skills, name='skills'),
    
    # CRUD ops
    path('add/', views.add_skill, name='add_skill'),
    path('update/<uuid:skills_id>/', views.update_skill, name='update_skill'),
    path('delete/<uuid:skills_id>/', views.delete_skill, name='delete_skill'),
    
    # AJAX endpoints
    path('skills/data/<uuid:skill_id>/', views.get_skill_data, name='get_skill_data'),
    path('skills/categories/', views.get_user_categories, name='get_user_categories'),
]    