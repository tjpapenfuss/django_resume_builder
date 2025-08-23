from django.urls import path
from . import views

urlpatterns = [
    # ... your existing URLs ...
    
    # Education URLs
    path('', views.education, name='education'),
    path('add/', views.add_education, name='add_education'),
    path('update/<uuid:education_id>/', views.update_education, name='update_education'),
    path('delete/<uuid:education_id>/', views.delete_education, name='delete_education'),
    path('data/<uuid:education_id>/', views.get_education_data, name='get_education_data'),
]