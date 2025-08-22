# API imports
from rest_framework import generics
from rest_framework.permissions import AllowAny

# Django imports
from django.shortcuts import render

# Local imports
from users.models import User
from .serializers import UserSerializer

class RegisterUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

def home_view(request):
    return render(request, 'home.html')