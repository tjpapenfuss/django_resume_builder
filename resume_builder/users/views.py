from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from .forms import UserRegistrationForm, CustomAuthenticationForm, UserProfileForm

def home(request):
    """Home page view"""
    return render(request, 'home.html')

def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Account created successfully! You can now log in.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'user/register.html', {'form': form})

def custom_login(request):
    """Custom login view using email instead of username"""
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            # Then increment login count
            user.login_count += 1
            user.save()
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.email}!')
            return redirect('home')  # or wherever you want to redirect after login
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'user/login.html', {'form': form})

@login_required
def profile(request):
    """User profile view"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'user/profile.html', {'form': form})

# Add this to your existing views
def logout_view(request):
    logout(request)
    #messages.success(request, 'You have been successfully logged out.')
    return redirect('login') 