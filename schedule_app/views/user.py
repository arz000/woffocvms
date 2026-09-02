from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from schedule_app.forms import UserProfileForm

@login_required
def user_profile_view(request):
    """Renders the detailed user profile page (Tailwind Admin style)."""
    form = UserProfileForm(request.POST or None, user=request.user)
    
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('user_profile')
        
    context = {
        'form': form,
    }
    return render(request, 'shared/my-profile.html', context)

def user_dashboard_view(request):
    """Renders the main dashboard for authenticated users."""
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'user/user-dashboard.html')
