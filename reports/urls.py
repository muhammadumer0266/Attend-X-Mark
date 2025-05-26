from django.urls import path
from . import views


urlpatterns = [
    path('lectures/', views.teacher_lectures_report, name='teacher_lectures_report'),
    path('lecture/<int:lecture_id>/attendance/delete/<int:attendance_record_id>/', views.delete_attendance, name='delete_attendance'),
    path('lectures/<int:lecture_id>/report/', views.student_attendance_report, name='student_attendance_report'),
]