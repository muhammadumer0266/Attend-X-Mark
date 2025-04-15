from django.urls import path
from . import views

urlpatterns = [
    path('leave/request/', views.leave_request, name='leave_request'),
    path('leave/list/', views.leave_list, name='leave_list'),
    path('lectures/', views.lecture_list, name='lecture_list'),
    path('lectures/<int:lecture_id>/', views.lecture_list, name='lecture_detail'),
    path('leave-approve/<int:leave_id>/', views.leave_approve, name='leave_approve'),
    path('leave-decline/<int:leave_id>/', views.leave_decline, name='leave_decline'),
    path('capture-face/', views.capture_face, name='capture_face'),
    path('capture/success/<str:captured_face_ids>/', views.capture_success, name='capture_success'),
    path('attendance/mark/<int:lecture_id>/<int:class_id>/', views.mark_attendance, name='mark_attendance'),
]