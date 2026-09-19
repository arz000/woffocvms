from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm, SetPasswordForm as DjangoSetPasswordForm

# Reusable Tailwind classes for inputs
INPUT_CLASSES = "block w-full rounded-2xl border border-gray-200 dark:border-gray-800 py-3 px-4 text-gray-900 dark:text-white placeholder:text-gray-400 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm font-medium bg-gray-50/60 dark:bg-gray-950/60 hover:bg-gray-50 dark:hover:bg-gray-950 transition-all outline-none"

class DirectPasswordResetForm(forms.Form):
    identity = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'Enter your username or email',
            'required': True,
            'autocomplete': 'username'
        })
    )
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'Enter new password',
            'required': True,
            'autocomplete': 'new-password'
        })
    )
    confirm_password = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'Confirm new password',
            'required': True,
            'autocomplete': 'new-password'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        identity = cleaned_data.get('identity', '').strip()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if identity:
            user = User.objects.filter(username__iexact=identity).first()
            if not user:
                user = User.objects.filter(email__iexact=identity).first()
            
            if not user:
                self.add_error('identity', 'No account found with that username or email address.')
            else:
                cleaned_data['user'] = user

        if new_password and confirm_password:
            if new_password != confirm_password:
                self.add_error('confirm_password', 'Passwords do not match.')
            elif len(new_password) < 6:
                self.add_error('new_password', 'Password must be at least 6 characters long.')

        return cleaned_data


class PasswordResetRequestForm(DjangoPasswordResetForm):
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'name@example.com',
            'required': True,
            'autocomplete': 'email'
        })
    )

class CustomSetPasswordForm(DjangoSetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = INPUT_CLASSES



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
    GENDER_CHOICES = [
        ('', 'Select Gender'),
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    # Personal Info (from User)
    first_name = forms.CharField(label="First Name", widget=forms.TextInput(attrs={'class': INPUT_CLASSES}))
    last_name = forms.CharField(label="Last Name", widget=forms.TextInput(attrs={'class': INPUT_CLASSES}))
    email = forms.EmailField(label="Email Address", widget=forms.EmailInput(attrs={'class': INPUT_CLASSES}))
    
    # Personal Info (from Profile)
    phone_number = forms.CharField(label="Phone Number", required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASSES}))
    gender = forms.ChoiceField(label="Gender", choices=GENDER_CHOICES, required=False, widget=forms.Select(attrs={'class': INPUT_CLASSES}))
    birthday = forms.DateField(label="Birthday", required=False, widget=forms.DateInput(attrs={'class': INPUT_CLASSES, 'type': 'date'}))
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
                self.fields['gender'].initial = profile.gender
                self.fields['birthday'].initial = profile.birthday
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
            profile.gender = self.cleaned_data.get('gender')
            profile.birthday = self.cleaned_data.get('birthday')
            profile.bio = self.cleaned_data.get('bio')
            profile.country = self.cleaned_data.get('country')
            profile.city_state = self.cleaned_data.get('city_state')
            profile.postal_code = self.cleaned_data.get('postal_code')
            profile.save()
