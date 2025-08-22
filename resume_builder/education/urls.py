from django.urls import path
from . import views

urlpatterns = [    
    # Authentication URLs
    path('add/', views.add_education, name='add_education'),  # Using custom login view
    
    # User profile
    path('update/', views.update_education, name='update_education'),
]
