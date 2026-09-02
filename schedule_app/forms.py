from django import forms
from django.contrib.auth.models import User

# Reusable Tailwind classes for inputs
INPUT_CLASSES = "block w-full rounded-2xl border border-gray-200 dark:border-gray-800 py-3 px-4 text-gray-900 dark:text-white placeholder:text-gray-400 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm font-medium bg-gray-50/60 dark:bg-gray-950/60 hover:bg-gray-50 dark:hover:bg-gray-950 transition-all outline-none"

class LoginForm(forms.Form):
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASSES,
            'required': True
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASSES,
            'required': True
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        label="Remember for 30 days",
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 rounded-md border-gray-300 text-blue-600 focus:ring-blue-600 cursor-pointer',
        })
    )


class RegisterForm(forms.ModelForm):
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASSES,
            'required': True
        })
    )
    first_name = forms.CharField(
        label="First Name",
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASSES,
            'required': True
        })
    )
    last_name = forms.CharField(
        label="Last Name",
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASSES,
            'required': True
        })
    )
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'class': INPUT_CLASSES,
            'required': True
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASSES,
            'required': True
        })
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password']


class UserProfileForm(forms.Form):
    # Personal Info (from User)
    first_name = forms.CharField(label="First Name", widget=forms.TextInput(attrs={'class': INPUT_CLASSES}))
    last_name = forms.CharField(label="Last Name", widget=forms.TextInput(attrs={'class': INPUT_CLASSES}))
    email = forms.EmailField(label="Email Address", widget=forms.EmailInput(attrs={'class': INPUT_CLASSES}))
    
    # Personal Info (from Profile)
    phone_number = forms.CharField(label="Phone Number", required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASSES}))
    bio = forms.CharField(label="Bio", required=False, widget=forms.Textarea(attrs={'class': INPUT_CLASSES, 'rows': 4}))
    
    # Address Info (from Profile)
    country = forms.CharField(label="Country", required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASSES}))
    city_state = forms.CharField(label="City/State", required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASSES}))
    postal_code = forms.CharField(label="Postal Code", required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASSES}))
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email
            
            profile = getattr(self.user, 'volunteer_profile', None)
            if profile:
                self.fields['phone_number'].initial = profile.phone_number
                self.fields['bio'].initial = profile.bio
                self.fields['country'].initial = profile.country
                self.fields['city_state'].initial = profile.city_state
                self.fields['postal_code'].initial = profile.postal_code

    def save(self):
        if not self.user:
            return
            
        # Update User
        self.user.first_name = self.cleaned_data.get('first_name')
        self.user.last_name = self.cleaned_data.get('last_name')
        self.user.email = self.cleaned_data.get('email')
        self.user.save()
        
        # Update Profile
        profile = getattr(self.user, 'volunteer_profile', None)
        if profile:
            profile.phone_number = self.cleaned_data.get('phone_number')
            profile.bio = self.cleaned_data.get('bio')
            profile.country = self.cleaned_data.get('country')
            profile.city_state = self.cleaned_data.get('city_state')
            profile.postal_code = self.cleaned_data.get('postal_code')
            profile.save()
