"""
URL configuration for axm_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView


urlpatterns = [
    # Redirect to accounts login as the default app
    path('', RedirectView.as_view(url='/accounts/login/', permanent=True)),
    
    # Admin site
    path('admin/', admin.site.urls),
    
    # Accounts app (default app)
    path('accounts/', include('accounts.urls')),

    # Other apps
    path('subjects/', include('subjects.urls')),
    path('attendance/', include('attendance.urls')),
    
    # PWA URLs (this should always be included to enable PWA on every page)
    path('', include('pwa.urls')),  # This must come after other apps to avoid conflicts
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
