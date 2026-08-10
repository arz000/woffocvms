from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from .models import Member, Activity, Post, Like, Comment, Notification
from .forms import RegistrationForm, ActivityForm, PostForm


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
            first_name=first_name,
            last_name=last_name,
            password=password,
         )

         Member.objects.create(
            user=user,
            email=email,
            first_name=first_name,
            last_name=last_name,
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

@login_required
def main(request):
    posts = Post.objects.all().order_by('-created_at')
    post_form = PostForm()

    for post in posts:
        post.user_liked = Like.objects.filter(
            post=post,
            user=request.user
        ).exists()

    # Query notifications for sidebar / bell dropdown
    user_notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')

    unread_notifications_count = user_notifications.filter(is_read=False).count()

    context = {
        'posts': posts,
        'post_form': post_form,
        'user_notifications': user_notifications,
        'unread_notifications_count': unread_notifications_count,
    }

    return render(request, 'main.html', context)

@login_required
def create_post(request):
    if request.method == 'POST':
        post_form = PostForm(request.POST)
        if post_form.is_valid():
            post = post_form.save(commit=False)
            post.author = request.user
            post.save()

            # 1. Fetch all users except the author (Admin)
            users_to_notify = User.objects.exclude(id=request.user.id)

            # 2. Prepare notification objects for bulk insert
            notifications = [
                Notification(
                    recipient=user,
                    sender=request.user,
                    post=post,
                    notification_type='post'
                )
            for user in users_to_notify
        ]
            
            # 3. Save all notifications in a single SQL query
            Notification.objects.bulk_create(notifications)      

        return redirect('main')
   
    return redirect('main')

@login_required
def like_post(request, post_id):

    if request.method != 'POST':
        return JsonResponse(
            {'error': 'Invalid request'},
            status=400
        )

    post = get_object_or_404(Post, id=post_id)
    like = Like.objects.filter(
        user=request.user,
        post=post
    )

    if like.exists():
        like.delete()
        liked = False
    else:
        Like.objects.create(
            user=request.user,
            post=post
        )
        liked = True

    # Only send notification when liking
    if request.user != post.author:
        Notification.objects.create(
        recipient=post.author,
        sender=request.user,
        post=post,
        notification_type='like'
    )

    return JsonResponse({
        'liked': liked,
        'likes_count': post.likes.count()
    })

@login_required
def create_comment(request, post_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Must be a POST request'}, status=400)

    post = get_object_or_404(Post, id=post_id)
    content = (request.POST.get('content') or request.POST.get('comment') or '').strip()

    if not content:
        return JsonResponse({'success': False, 'error': 'Comment content cannot be empty'}, status=400)

    comment = Comment.objects.create(
        post=post,
        author=request.user,
        content=content
    )
    notifications_to_create = []

    # 1. Notify Post Author (if not commenting on their own post)
    if request.user != post.author:
        notifications_to_create.append(
            Notification(
                recipient=post.author,
                sender=request.user,
                post=post,
                notification_type='comment'
            )
        )

    # 2. Get distinct previous commenter IDs
    previous_commenter_ids = Comment.objects.filter(post=post)\
        .exclude(author=request.user)\
        .exclude(author=post.author)\
        .values_list('author_id', flat=True)\
        .distinct()

    # 3. Build notification list using recipient_id directly (no extra User query)
    for user_id in previous_commenter_ids:
        notifications_to_create.append(
            Notification(
                recipient_id=user_id,
                sender=request.user,
                post=post,
                notification_type='comment'
            )
        )
        
    if notifications_to_create:
        Notification.objects.bulk_create(notifications_to_create)

    return JsonResponse({
        'success': True,
        'author': comment.author.username,
        'content': comment.content,
        'comments_count': post.comments.count()
    })
@login_required
def mark_notifications_read(request):

    Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(is_read=True)

    return JsonResponse({
        'success': True
    })

@login_required
def profile(request):
    member = get_object_or_404(Member, user=request.user)
    context = {'member': member}
    return render(request, 'profile.html', context)

@login_required
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

@login_required
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

def message(request):
    return render(request, 'message.html')

def search(request):
    return render(request, 'search.html')

def notification(request):
    return render(request, 'notification.html')

