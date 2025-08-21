from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path('successful-login/', views.successful_login_view, name='successful_login'),
]
