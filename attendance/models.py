from django.db import models
from django.conf import settings
from accounts.models import Student
from subjects.models import Course, Semester, Class
from django.utils import timezone
from django.core.exceptions import ValidationError

class Leave(models.Model):
    STATUS_CHOICES = [('Pending', 'Pending'), ('Approved', 'Approved'), ('Declined', 'Declined')]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, default=None, limit_choices_to={'is_staff': True}, related_name='teacher_leaves')
    subject = models.CharField(max_length=200)
    body = models.TextField()
    leave_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.first_name} - {self.subject} ({self.status})"

class CapturedFace(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='captured_faces/')
    captured_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.first_name} - {self.captured_at}"

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

class Lecture(models.Model):
    lecture_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lectures')
    lecture_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='lectures')
    start_time = models.TimeField()
    end_time = models.TimeField()
    days = models.ManyToManyField(Day, related_name='lectures')
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'is_staff': True},
        related_name='lectures_taught',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Lecture"
        verbose_name_plural = "Lectures"

    def __str__(self):
        return f"{self.course.code}"

    @property
    def duration(self):
        from datetime import datetime
        start = datetime.combine(datetime.today(), self.start_time)
        end = datetime.combine(datetime.today(), self.end_time)
        return (end - start).seconds // 60

    def days_display(self):
        return ', '.join(day.name for day in self.days.all())

class Attendance(models.Model):
    lecture = models.ForeignKey(Lecture, on_delete=models.SET_NULL, null=True, related_name='attendances')
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, related_name='attendances')
    date = models.DateField(default=timezone.now)
    is_makeup = models.BooleanField(default=False)
    status = models.CharField(
        max_length=7,
        choices=[
            ('Present', 'Present'),
            ('Absent', 'Absent'),
            ('Leave', 'Leave'),
        ],
        default='Absent'
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Attendance"
        verbose_name_plural = "Attendances"
        constraints = [
            models.UniqueConstraint(
                fields=['lecture', 'student', 'date', 'is_makeup'],
                name='unique_attendance_per_lecture_student_date_makeup'
            )
        ]

    def clean(self):
        # Validate that the student belongs to the lecture's class
        if self.student and self.lecture and self.lecture.lecture_class:
            if self.student not in self.lecture.lecture_class.students:
                raise ValidationError(f"Student {self.student} does not belong to class {self.lecture.lecture_class}")
        
        # Validate that Leave status is consistent with approved leave
        if self.status == 'Leave' and self.date:
            leave_exists = Leave.objects.filter(
                user=self.student,
                leave_date=self.date,
                status='Approved'
            ).exists()
            if not leave_exists:
                raise ValidationError("Cannot mark as Leave without an approved leave request for this date.")

    def __str__(self):
        return f"{self.student} - {self.lecture} - {self.date} ({'Makeup' if self.is_makeup else 'Regular'})"