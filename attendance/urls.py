from django.urls import path
from . import views

urlpatterns = [
    path('leave/request/', views.leave_request, name='leave_request'),
    path('leave/list/', views.leave_list, name='leave_list'),
    path('lectures/', views.lecture_list, name='lecture_list'),
    path('leave-approve/<int:leave_id>/', views.leave_approve, name='leave_approve'),
    path('leave-decline/<int:leave_id>/', views.leave_decline, name='leave_decline'),
    path('mark/<int:lecture_id>/<int:is_makeup_class>/', views.mark_attendance, name='mark_attendance'),
    path('makeup/<int:lecture_id>/', views.add_makeup_class, name='add_makeup_class'),
    path('success/', views.attendance_success, name='attendance_success'),
    path('capture/<int:lecture_id>/', views.capture_face, name='capture_face'),
    path('', views.student_attendance, name='student_attendance'),
    path('attendance/<int:semester_id>/<int:course_id>/', views.attendance_details, name='attendance_details'),
    path('lectures/<int:lecture_id>/edit/<int:attendance_record_id>/', views.edit_attendance, name='edit_attendance'),
]