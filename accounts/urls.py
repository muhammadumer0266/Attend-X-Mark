from django.urls import path
from .views import register, dashboard, profile, CustomLoginView, custom_logout_view, personal_info,profile_settings
from django.conf import settings
from django.conf.urls.static import static
from . import views
urlpatterns = [
    path('', views.home, name='home'),
    path('register/', register, name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('logout/', custom_logout_view, name='logout'),
    path('personal-info/', personal_info, name='personal_info'),
    path('dashboard/', dashboard, name='dashboard'),
    path('profile/', profile, name='profile'),
    path('accounts/pending/', views.account_pending_view, name='account_pending'),
    path('privacy-policy', views.privacy_policy, name='privacy_policy'),
    path('profile/settings/', profile_settings, name='profile_settings'),
    path('offline/', views.offline, name='offline'),
    path('generate-personal-info-otp/', views.generate_personal_info_otp, name='generate_personal_info_otp'),
    path('pending/', views.account_pending_view, name='account_pending'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
