from django.urls import path
from .views import register, dashboard, profile, CustomLoginView, custom_logout_view, personal_info,profile_settings
from django.conf import settings
from django.conf.urls.static import static
from . import views
urlpatterns = [
    path('', views.home, name='home'),
    path('register/', register, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('logout/', custom_logout_view, name='logout'),
    path('personal-info/', views.personal_info, name='personal_info'),
    path('dashboard/', dashboard, name='dashboard'),
    path('profile/', profile, name='profile'),
    path('pending/', views.pending, name='pending'),
    path('privacy-policy', views.privacy_policy, name='privacy_policy'),
    path('profile/settings/', profile_settings, name='profile_settings'),
    path('profile/teacher/update-info/', views.update_teacher_info, name='update_teacher_info'),
    path('unblock-device/', views.unblock_device_request, name='unblock_device_request'),
    path('unblock-device/verify/', views.unblock_device_verify, name='unblock_device_verify'),
    path('offline/', views.offline, name='offline'),
    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
