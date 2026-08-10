from django.urls import path
from . import views

urlpatterns = [
    path('', views.first_page, name='first_page'),
    
    path('register/', views.register, name='register'),
    path('login-page/', views.login_page, name='login_page'),
    path('logout/', views.logout_user, name='logout'),

    # Main Tab
    path('main/', views.main, name='main'),
    path('create-post/', views.create_post, name='create_post'),
    path('like-post/<int:post_id>/', views.like_post, name='like_post'),
    path('comment-post/<int:post_id>/', views.create_comment, name='comment_post'),
    path('notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),

    # About Us Tab
    path('about_us/', views.about_us, name='about_us'),

    # Profile Tab
    path('profile/', views.profile, name='profile'),
    path('myactivity/', views.myactivity, name='myactivity'),
    path('myactivity/edit-activity/<int:id>/', views.edit_activity, name='edit_activity'),
    path("myactivity/delete-activity/<int:id>/", views.delete_activity, name="delete_activity"),

    # ADMIN(View Member)
    path('view_member/', views.members, name='members'),
    path('view_member/details/<int:id>/', views.details, name='details'),

    # Others Tab
    path('message/', views.message, name='message'),
    path('search/', views.search, name='search'),
    path('notification/', views.notification, name='notification'),
]
