from django import forms
from .models import Member, Activity, Post

class RegistrationForm(forms.Form):
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "First Name"
        })
    )

    last_name = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Last Name"
        })
    )

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Username",
            "autocomplete": "username"

        })
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Email Address"
        })
    )

    phone = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Phone Number"
        })
    )

    birth_date = forms.DateField(
        widget=forms.DateInput(attrs={
            "class": "form-control",
            "type": "date"
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Password"
        })
    )


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = [
            'title',
            'description',
            'activity_date',
        ]

        widgets = {
            'title': forms.TextInput(attrs={
                'id': 'titleField',
                'class': 'form-control',
                'placeholder': 'Activity Title'
            }),

            'description': forms.Textarea(attrs={
                'id': 'descriptionField',
                'class': 'form-control',
                'placeholder': 'Description',
                'rows': 4
            }),

            'activity_date': forms.DateInput(attrs={
                'id': 'dateField',
                'class': 'form-control',
                'type': 'date'
            }),
        }
    
class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Post Title',
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'What\'s on your mind?',
                'rows': 4,
            }),
        }
# class Member(forms.Form):
#     class Meta:
#         model = Member

#         fields = [
#             "phone",
#             "birth_date",
#         ]