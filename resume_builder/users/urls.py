from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    # path('successful-login/', views.successful_login_view, name='successful_login'),
    path('profile/', views.profile_view, name='profile'),  
    path('logout/', views.logout_view, name='logout'),  
]
