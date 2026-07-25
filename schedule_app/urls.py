from django.urls import path
from . import views

urlpatterns = [
    path('first-page/', views.first_page, name='first_page'),

    path('register/', views.register, name='register'),
    path('login-page/', views.login_page, name='login_page'),
    path('logout/', views.logout_user, name='logout'),

    path('main/', views.main, name='main'),
    path('about_us/', views.about_us, name='about_us'),

    path('profile/', views.profile, name='profile'),
    
    path('myactivity/', views.myactivity, name='myactivity'),
    path('myactivity/edit-activity/<int:id>/', views.edit_activity, name='edit_activity'),
    path("myactivity/delete-activity/<int:id>/", views.delete_activity, name="delete_activity"),

    path('view_member/', views.members, name='members'),
    path('view_member/details/<int:id>/', views.details, name='details'),

   
]
