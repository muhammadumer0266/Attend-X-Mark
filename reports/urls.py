from django.urls import path
from . import views


urlpatterns = [
    path('lectures/', views.teacher_lectures_report, name='teacher_lectures_report'),
    path('lectures/<int:lecture_id>/report/', views.student_attendance_report, name='student_attendance_report'),
]