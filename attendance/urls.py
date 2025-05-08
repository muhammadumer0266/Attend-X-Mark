from django.urls import path
from . import views

urlpatterns = [
    path('leave/request/', views.leave_request, name='leave_request'),
    path('leave/list/', views.leave_list, name='leave_list'),
    path('lectures/', views.lecture_list, name='lecture_list'),
    path('lectures/<int:lecture_id>/', views.lecture_list, name='lecture_detail'),
    path('leave-approve/<int:leave_id>/', views.leave_approve, name='leave_approve'),
    path('leave-decline/<int:leave_id>/', views.leave_decline, name='leave_decline'),
    path('mark/<int:lecture_id>/', views.mark_attendance, name='mark_attendance'),
    path('makeup/<int:lecture_id>/', views.add_makeup_class, name='add_makeup_class'),
    path('success/', views.attendance_success, name='attendance_success'),
    path('lectures/<int:lecture_id>/report/', views.student_attendance_report, name='student_attendance_report'),
    path('capture/<int:lecture_id>/', views.capture_face, name='capture_face'),  # Updated to include lecture_id
    path('capture/success/', views.capture_success, name='capture_success'),
]