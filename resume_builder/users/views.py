from .forms import UserRegistrationForm
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserRegistrationForm, CustomAuthenticationForm, UserProfileForm
from django.contrib.auth.forms import UserCreationForm

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)  # Or your custom form
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Account created successfully!')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'user/register.html', {'form': form})

# def register(request):
#     if request.method == "POST":
#         form = UserRegistrationForm(request.POST)
#         if form.is_valid():
#             form.save()
#             return redirect("login")  # redirect to login page or dashboard
#     else:
#         form = UserRegistrationForm()
#     return render(request, "user/register.html", {"form": form})

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'user/profile.html', {'form': form, 'user': request.user})

def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        
        if form.is_valid():
            user = form.get_user()
            if user:
                # Log the user in first
                login(request, user)
                
                # Then increment login count
                user.login_count += 1
                user.save()
                                
                return redirect('profile')
            else:
                print("get_user() returned None")  # Debug
        else:
            print(f"Form errors: {form.errors}")  # Debug
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'user/login.html', {'form': form})


# Add this to your existing views
def logout_view(request):
    logout(request)
    #messages.success(request, 'You have been successfully logged out.')
    return redirect('login') 