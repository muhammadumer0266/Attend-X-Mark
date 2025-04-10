from django.db import models
from django.conf import settings
from accounts.models import Student
from subjects.models import Course, Semester

class Leave(models.Model):
    STATUS_CHOICES = [('Pending', 'Pending'), ('Approved', 'Approved'), ('Declined', 'Declined')]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, default=None, limit_choices_to={'is_staff': True}, related_name='teacher_leaves')
    subject = models.CharField(max_length=200)
    body = models.TextField()
    leave_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.user.first_name} - {self.subject} ({self.status})"

class CapturedFace(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='captured_faces/')
    captured_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.user.first_name} - {self.captured_at}"

class Attendance(models.Model):
    attendance_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=[('Present', 'Present'), ('Absent', 'Absent'), ('Late', 'Late')])
    room = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = "Attendance"
        verbose_name_plural = "Attendances"

    def __str__(self): return f"{self.student.username} - {self.date} ({self.status})"

from django.db import models
from django.conf import settings  # To use AUTH_USER_MODEL

# New Day model
class Day(models.Model):
    name = models.CharField(
        max_length=9,
        choices=[
            ('Monday', 'Monday'),
            ('Tuesday', 'Tuesday'),
            ('Wednesday', 'Wednesday'),
            ('Thursday', 'Thursday'),
            ('Friday', 'Friday'),
            ('Saturday', 'Saturday'),
            ('Sunday', 'Sunday'),
        ],
        unique=True,
    )

    def __str__(self):
        return self.name

from subjects.models import Class
class Lecture(models.Model):
    lecture_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lectures')
    lecture_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='lectures')
    attendance = models.ManyToManyField(Attendance, blank=True, related_name='lectures')
    start_time = models.TimeField()
    end_time = models.TimeField()
    days = models.ManyToManyField(Day, related_name='lectures')  # Many-to-many relationship
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'is_staff': True},  # Restrict to staff users (teachers)
        related_name='lectures_taught',
        null=True,
        blank=True  # Optional: Allow lectures without a teacher
    )

    class Meta:
        verbose_name = "Lecture"
        verbose_name_plural = "Lectures"

    def __str__(self):
        return f"{self.course.code}"

    @property
    def duration(self):
        from datetime import datetime
        start = datetime.combine(self.date, self.start_time)
        end = datetime.combine(self.date, self.end_time)
        return (end - start).seconds // 60

    # Optional: Helper method to display days
    def days_display(self):
        return ', '.join(day.name for day in self.days.all())