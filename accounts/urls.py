from django.urls import path
from .views import register, dashboard, profile, CustomLoginView, custom_logout_view, personal_info,profile_settings
from django.conf import settings
from django.conf.urls.static import static
from . import views
urlpatterns = [
    path('home/', views.home, name='home'),
    path('register/', register, name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', custom_logout_view, name='logout'),
    path('personal-info/', views.personal_info, name='personal_info'),
    path('dashboard/', dashboard, name='dashboard'),
    path('profile/', profile, name='profile'),
    path('pending/', views.pending, name='pending'),
    path('profile/settings/', profile_settings, name='profile_settings'),
    path('profile/teacher/update-info/', views.update_teacher_info, name='update_teacher_info'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
