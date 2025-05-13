from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axm_project.settings')

app = Celery('axm_project')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')