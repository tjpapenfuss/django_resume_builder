from django.shortcuts import render, redirect
from .forms import UserRegistrationForm
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required

from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from .forms import UserRegistrationForm, CustomAuthenticationForm  # Import both forms

def register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("login")  # redirect to login page or dashboard
    else:
        form = UserRegistrationForm()
    return render(request, "user/register.html", {"form": form})


def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('successful_login')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'login.html', {'form': form})

# Add this new view for successful login
def successful_login_view(request):
    return render(request, 'user/successful_login.html')