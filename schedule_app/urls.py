from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # Public Routes
    path('', RedirectView.as_view(url='/login/', permanent=False), name='landing_page'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password Reset Routes
    path('forgot-password/', views.password_reset_view, name='password_reset'),
    path('forgot-password/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),


    
    # User / Volunteer Routes
    path('user-dashboard/', views.user_dashboard_view, name='user_dashboard'),
    path('profile/', views.user_profile_view, name='user_profile'),
    path('volunteer/calendar/', views.volunteer_calendar_view, name='volunteer_calendar'),
    path('volunteer/schedule/', views.volunteer_schedule_view, name='volunteer_schedule'),
    path('volunteer/opportunities/', views.volunteer_opportunities_view, name='volunteer_opportunities'),
    path('volunteer/create-shift/', views.volunteer_create_shift_view, name='volunteer_create_shift'),

    # Department Head Routes
    path('dept-head/events/', views.dept_head_events_view, name='dept_head_events'),
    path('dept-head/events/<int:event_id>/', views.dept_head_event_detail_view, name='dept_head_event_detail'),
    path('dept-head/availability/', views.dept_head_availability_view, name='dept_head_availability'),
    path('dept-head/jobs/', views.dept_head_jobs_view, name='dept_head_jobs'),
    
    # Admin Routes
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin-schedule/', views.admin_schedule_view, name='admin_schedule'),
    path('admin-service/', views.admin_service_view, name='admin_service'),
    path('admin-departments/', views.admin_departments_view, name='admin_departments'),
    path('admin-members/', views.admin_members_view, name='admin_members'),
    path('admin-user-roles/', views.admin_user_roles_view, name='admin_user_roles'),
    path('admin-activity-log/', views.admin_activity_log_view, name='admin_activity_log'),
    path('api/update-role/', views.api_update_role, name='api_update_role'),
    path('api/assign-role/', views.api_assign_role, name='api_assign_role'),
    path('api/remove-role/', views.api_remove_role, name='api_remove_role'),
    path('search-volunteers/', views.search_volunteers, name='search_volunteers'),
    path('api/update-ministries/', views.api_update_ministries, name='api_update_ministries'),

    # Delete records
    path('api/delete-record/', views.api_delete_record, name='api_delete_record'),
    path('api/create-capability/', views.api_create_capability, name='api_create_capability'),


   
]
