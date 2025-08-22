from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    
    # Authentication URLs
    path('login/', views.custom_login, name='login'),  # Using custom login view
    path('logout/', views.logout_view, name='logout'),  
    path('register/', views.register, name='register'),
    
    # User profile
    path('profile/', views.profile, name='profile'),
]
