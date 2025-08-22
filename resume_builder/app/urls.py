from django.urls import path
from .views import home_view, RegisterUserView

urlpatterns = [
    path('', home_view, name='home'),
    path('api/register/', RegisterUserView.as_view(), name='api_register'),
    # Future development
    # path('about/', views.about_view, name='about'),
    # path('resumes/', views.resume_list_view, name='resume_list'),
]