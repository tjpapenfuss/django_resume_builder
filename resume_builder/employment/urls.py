from django.urls import path
from . import views

urlpatterns = [
    # ... your existing URLs ...
    
    # employment URLs
    path('', views.employment, name='employment'),
    path('add/', views.add_employment, name='add_employment'),
    path('update/<uuid:employment_id>/', views.update_employment, name='update_employment'),
    path('delete/<uuid:employment_id>/', views.delete_employment, name='delete_employment'),
    path('data/<uuid:employment_id>/', views.get_employment_data, name='get_employment_data'),
]