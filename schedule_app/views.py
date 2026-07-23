from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from .models import Member, Activity
from .forms import RegistrationForm, ActivityForm


# Create your views here.
def first_page(request):
   return render(request, 'firstpage.html')

def register(request):
   if request.method == 'POST':
      form = RegistrationForm(request.POST)
      if form.is_valid():
         first_name = form.cleaned_data["first_name"]
         last_name = form.cleaned_data["last_name"]
         username = form.cleaned_data["username"]
         email = form.cleaned_data["email"]
         phone = form.cleaned_data["phone"]
         birth_date = form.cleaned_data["birth_date"]
         password = form.cleaned_data["password"]

         user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
         )

         Member.objects.create(
            user=user,
            phone=phone,
            birth_date=birth_date,
         )

         return redirect('login_page')
   else:
      form = RegistrationForm()

   return render(request, "register.html", {"form": form})

def login_page(request):
   if request.method == "POST":
      username = request.POST["username"]
      password = request.POST["password"]

      user = authenticate(request,username=username,password=password)

      if user is not None:
         login(request, user)
         return redirect("main")
      return render(request, 'login.html', {'error': 'Invalid username or password'})   
   
   return render(request, 'login.html')

def logout_user(request):
    if request.method == "POST":
        logout(request)
    return render(request, "firstpage.html")

def main(request):
   return render(request, 'main.html')

@login_required(login_url='login_page')
def myactivity(request):
    if request.method == 'POST':
        form = ActivityForm(request.POST)

        if form.is_valid():
            activity = form.save(commit=False)
            activity.member = request.user.member
            activity.save()
            return redirect('myactivity')
        
    else:
        form = ActivityForm()

    activities = Activity.objects.filter(member=request.user.member).order_by('-created_at')

    paginator = Paginator(activities, 3)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'form': form,
        'page_obj': page_obj,
    }

    return render(request, 'activity.html', context)

def edit_activity(request, id):
   activity = get_object_or_404(Activity, id=id, member=request.user.member)
   if request.method == "POST":
      form = ActivityForm(request.POST, instance=activity)
      if form.is_valid():
         form.save()
         return redirect("myactivity")
   return redirect("myactivity")

@login_required
def delete_activity(request, id):
    activity = get_object_or_404(Activity,id=id,member=request.user.member)
    if request.method == "POST":
        activity.delete()
    return redirect("myactivity")

@login_required(login_url='login_page')
def members(request):
    mymembers = Member.objects.select_related('user').all()
    context = {'mymembers': mymembers}
    return render(request, 'members.html', context)

def details(request, id):
  mymembers = Member.objects.select_related('user').get(id=id)
  context = {'mymembers': mymembers}
  return render(request, 'details.html', context)


def about_us(request):
    return render(request, 'aboutUs.html')