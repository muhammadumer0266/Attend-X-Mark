from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.shortcuts import redirect

def custom_admin_login_redirect(request):
    return redirect("login")

urlpatterns = [
    path("admin/login/",custom_admin_login_redirect),
    path('', include('pwa.urls')),
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('subjects/', include('subjects.urls')),
    path('attendance/', include('attendance.urls')),
    path('report/', include('reports.urls')),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
