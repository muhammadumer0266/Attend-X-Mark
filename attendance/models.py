from django.db import models
from django.conf import settings
from accounts.models import Student
from subjects.models import Course, Semester, Class
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver

class Leave(models.Model):
    STATUS_CHOICES = [('Pending', 'Pending'), ('Approved', 'Approved'), ('Declined', 'Declined')]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lecture = models.ForeignKey('Lecture', on_delete=models.CASCADE, related_name='leaves', null=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    leave_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.first_name} - {self.subject} ({self.status})"

    def save(self, *args, **kwargs):
        # Automatically decline leave if date has passed
        if self.leave_date < timezone.now().date():
            self.status = 'Declined'
        super().save(*args, **kwargs)

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
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('ended', 'Ended'),
    ]
    lecture_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lectures')
    lecture_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='lectures')
    start_time = models.TimeField()
    end_time = models.TimeField()
    days = models.ManyToManyField(Day, related_name='lectures')
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'is_teacher': True},
        related_name='lectures_taught',
        null=True,
        blank=True
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

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

    def check_semester_mismatch(self):
        """Check if course and lecture_class belong to different semesters"""
        return self.course.semester != self.lecture_class.semester

    def update_status_if_needed(self):
        """Update status to 'ended' if semesters don't match"""
        if self.check_semester_mismatch() and self.status == 'active':
            self.status = 'ended'
            self.save(update_fields=['status'])

    def clean(self):
        if self.check_semester_mismatch():
            raise ValidationError("Course and Class must belong to the same semester.")

    def save(self, *args, **kwargs):
        if self.check_semester_mismatch():
            self.status = 'ended'
        super().save(*args, **kwargs)

@receiver(post_save, sender=Course)
def update_lectures_on_course_change(sender, instance, **kwargs):
    """Update lecture status when course semester changes"""
    lectures = Lecture.objects.filter(course=instance)
    for lecture in lectures:
        lecture.update_status_if_needed()

@receiver(post_save, sender=Class)
def update_lectures_on_class_change(sender, instance, **kwargs):
    """Update lecture status when class semester changes"""
    lectures = Lecture.objects.filter(lecture_class=instance)
    for lecture in lectures:
        lecture.update_status_if_needed()

class AttendanceRecord(models.Model):
    lecture = models.ForeignKey('Lecture', on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=timezone.now)
    is_makeup_class = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"

    def __str__(self):
        return f"{self.lecture} - {self.date}"

class Attendance(models.Model):
    ATTENDANCE_STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('leave', 'Leave'),
    ]

    attendance_record = models.ForeignKey('AttendanceRecord', on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    attendance_status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS_CHOICES)

    class Meta:
        unique_together = ('attendance_record', 'student')
        verbose_name = "Attendance"
        verbose_name_plural = "Attendances"

    def __str__(self):
        return f"{self.student} - {self.attendance_record.date} - {self.attendance_status}"