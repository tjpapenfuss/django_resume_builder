from django.urls import path
from . import views

app_name = 'experience'

urlpatterns = [
    # ... your existing URLs ...
    
    # employment URLs
    path('', views.experiences, name='experience'),
    path('add/', views.add_experience, name='add_experience'),
    path('update/<uuid:experience_id>/', views.update_experience, name='update_experience'),
    path('delete/<uuid:experience_id>/', views.delete_experience, name='delete_experience'),
    path('data/<uuid:experience_id>/', views.get_experience_data, name='get_experience_data'),
]