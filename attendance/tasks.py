from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_leave_notification_email(student_email, student_name, leave_subject, status):
    subject = f'Leave Request {status}'
    message = (
        f'Hello {student_name},\n\n'
        f'Your leave request with subject "{leave_subject}" has been processed.\n'
        f'Status: {status}\n\n'
        f'Best regards,\nThe AttendXMark Team'
    )
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [student_email]
    
    send_mail(
        subject,
        message,
        from_email,
        recipient_list,
        fail_silently=False,
    )