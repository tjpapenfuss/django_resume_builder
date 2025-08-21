from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.forms import AuthenticationForm

User = get_user_model()

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['email', 'password']

    def save(self, commit=True):
        user = User.objects.create_user(
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password']
        )
        if commit:
            user.save()
        return user

User = get_user_model()

class CustomAuthenticationForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Email'}),
        label='Email'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'}),
        label='Password'
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(
                self.request,
                email=email,
                password=password
            )
            if self.user_cache is None:
                raise forms.ValidationError("Please enter a correct email and password.")
            elif not self.user_cache.is_active:
                raise forms.ValidationError("This account is inactive.")

        return self.cleaned_data

    def get_user(self):
        return self.user_cache