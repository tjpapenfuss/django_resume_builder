from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.job_list, name='job_list'),
    path('add/', views.add_job_from_url, name='add_job_from_url'),
    path('<uuid:pk>/', views.job_detail, name='job_detail'),
    path('<uuid:pk>/extended/', views.job_detail_extended, name='job_detail_extended'),
    path('api/job/<uuid:pk>/analyze/', views.analyze_job_api, name='analyze_job_api'),
    path('<uuid:pk>/delete/', views.job_delete, name='job_delete'),
    path('dashboard/', views.dashboard, name='job_dashboard'),
    path('api/<uuid:pk>/skills/', views.job_skills_api, name='job_skills_api'),
    path('api/application/<uuid:pk>/status/', views.update_application_status, name='update_application_status'),
    path('<uuid:pk>/skill-gap/', views.job_skill_gap_simple, name='job_skill_gap'),
]