# run celery worker
# celery -A axm_project worker --loglevel=info --pool=solo

# celery beat run 
# celery -A axm_project beat --loglevel=info


from pathlib import Path
import os
SECRET_KEY = 'django-insecure-8-*qhr3$d$n==(h@i-0%iflzx=&od_mgojo-+6dk-3iu#=b+px'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = 'attendxmark@gmail.com'
EMAIL_HOST_PASSWORD = 'tyan iexe azgo noxp'
DEFAULT_FROM_EMAIL = 'attendxmark@gmail.com'
RECAPTCHA_PUBLIC_KEY = '6LePDycrAAAAAMSQgSt6VPkJKkt6BsZ2qW6BXxyI'
RECAPTCHA_PRIVATE_KEY = '6LePDycrAAAAAG5lOVFKBzxVxabJRF68LBZwEok4' 


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = True

ALLOWED_HOSTS = ['umerg.pythonanywhere.com',"127.0.0.1",'localhost',"0.0.0.0"]

INSTALLED_APPS = [
    "admin_interface",
    "colorfield",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'phonenumber_field',
    'accounts',       
    'django_recaptcha',
    'attendance',    
    'reports',       
    'subjects',      
    'pwa',
    'django_celery_beat',
]

##########            celery                              ##########################################################################
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Karachi' 
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
#############################################################################################################

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.CompleteProfileMiddleware',
]

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
############################################################             PWA                     ############################################################

PWA_APP_NAME = 'AttendXMark'
PWA_APP_DESCRIPTION = 'Smart Attendance Marking System'
PWA_APP_THEME_COLOR = '#1d3557'
PWA_APP_BACKGROUND_COLOR = '#ffffff'
PWA_APP_DISPLAY = 'standalone'
PWA_APP_SCOPE = '/'
PWA_APP_ORIENTATION = 'any'
PWA_APP_START_URL = '/'
PWA_APP_STATUS_BAR_COLOR = 'default'
PWA_APP_ICONS = [
    {'src': '/static/images/icon-160x160.png',
        'sizes': '160x160',
        'type': 'image/png'}
]
PWA_APP_ICONS_APPLE = [
    {'src': '/static/images/icon-160x 160.png',
        'sizes': '160x160',
        'type': 'image/png'}
]
PWA_APP_SPLASH_SCREEN = [
    {'src': '/static/images/icons/splash-640x1136.png',
        'media': '(device-width: 320px) and (device-height: 568px) and (-webkit-device-pixel-ratio: 2)'}
]
PWA_APP_DIR = 'ltr'
PWA_APP_LANG = 'en-US'
PWA_APP_SHORTCUTS = [
    {
        'name': 'Dashboard',
        'url': '/dashboard/',
        'description': 'Go to the dashboard'
    }
]

PWA_SERVICE_WORKER_PATH = os.path.join(BASE_DIR, 'axm_project', 'static', 'serviceworker.js')
#############################################################################################################

AUTH_USER_MODEL = 'accounts.CustomUser'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'
LOGIN_URL = '/login/'
ROOT_URLCONF = 'axm_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'axm_project.wsgi.application'

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3','NAME': BASE_DIR / 'db.sqlite3',}}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Karachi'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'axm_project', 'static'),
]