from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Leave, Lecture, Attendance, Day
from .forms import LeaveForm
from django.contrib import messages
from accounts.models import Student, CustomUser
from django.core.files.base import ContentFile
import face_recognition
import base64
import os
import json
from .models import CapturedFace
from django.http import JsonResponse
from datetime import date, timedelta, datetime
from django.conf import settings

@login_required
def leave_request(request):
    if request.method == 'POST':
        form = LeaveForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.user = request.user
            leave.save()
            return redirect('leave_list')
    else:
        form = LeaveForm()
    return render(request, 'attendance/leave_request.html', {'form': form})

@login_required
def leave_list(request):
    if request.user.is_superuser:
        leaves = Leave.objects.all().order_by('-created_at')
    elif request.user.is_teacher:
        leaves = Leave.objects.filter(teacher=request.user).order_by('-created_at')
    elif request.user.is_student:
        leaves = Leave.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'attendance/leave_list.html', {'leaves': leaves})

@login_required
def leave_approve(request, leave_id):
    leave = get_object_or_404(Leave, id=leave_id)
    leave.status = 'Approved'
    leave.save()
    return redirect('leave_list')

@login_required
def leave_decline(request, leave_id):
    leave = get_object_or_404(Leave, id=leave_id)
    leave.status = 'Declined'
    leave.save()
    return redirect('leave_list')

@login_required
def capture_face(request):
    if request.method == 'POST':
        image_data_json = request.POST.get('image_data[]')
        if image_data_json:
            image_data_list = json.loads(image_data_json)
            captured_face_ids = []

            for image_data in image_data_list:
                format, imgstr = image_data.split(';base64,')
                ext = format.split('/')[-1]
                image_file = ContentFile(base64.b64decode(imgstr), name=f'captured_image_{len(captured_face_ids) + 1}.{ext}')
                captured_face = CapturedFace(user=request.user, image=image_file)
                captured_face.save()
                captured_face_ids.append(captured_face.id)

            return redirect('capture_success', captured_face_ids=','.join(map(str, captured_face_ids)))
    
    return render(request, 'attendance/capture_face.html')

@login_required
def capture_success(request, captured_face_ids):
    try:
        face_ids = [int(id) for id in captured_face_ids.split(',')]
        captured_faces = CapturedFace.objects.filter(id__in=face_ids)
        
        total_faces_detected = 0
        matched_students = set()
        captured_images_info = []

        all_uploaded_encodings = []
        for captured_face in captured_faces:
            captured_image_path = os.path.join(settings.MEDIA_ROOT, captured_face.image.name)
            uploaded_image = face_recognition.load_image_file(captured_image_path)
            uploaded_face_locations = face_recognition.face_locations(uploaded_image)
            uploaded_face_encodings = face_recognition.face_encodings(uploaded_image, uploaded_face_locations)
            
            num_faces = len(uploaded_face_locations)
            total_faces_detected += num_faces
            captured_images_info.append({
                'url': captured_face.image.url,
                'user': captured_face.user,
                'faces_detected': num_faces
            })
            all_uploaded_encodings.extend(uploaded_face_encodings)

        if all_uploaded_encodings:
            all_users = CustomUser.objects.exclude(profile_picture='profile_pics/defpic.png')
            for user in all_users:
                if not user.is_student:
                    continue
                    
                profile_pic_path = os.path.join(settings.MEDIA_ROOT, user.profile_picture.name)
                if os.path.exists(profile_pic_path):
                    known_image = face_recognition.load_image_file(profile_pic_path)
                    known_encodings = face_recognition.face_encodings(known_image)
                    
                    if known_encodings:
                        for uploaded_encoding in all_uploaded_encodings:
                            matches = face_recognition.compare_faces([known_encodings[0]], uploaded_encoding)
                            if matches[0]:
                                distance = face_recognition.face_distance([known_encodings[0]], uploaded_encoding)[0]
                                if distance < 0.6:
                                    matched_students.add(user.username)
                                    break

        context = {
            'matched_students': list(matched_students),
            'total_faces_detected': total_faces_detected,
            'captured_images_info': captured_images_info,
        }
        return render(request, 'attendance/capture_success.html', context)

    except CapturedFace.DoesNotExist:
        return render(request, 'attendance/capture_face.html', {'error': 'Captured face not found'})
    except Exception as e:
        return render(request, 'attendance/capture_face.html', {'error': f'An error occurred: {str(e)}'})

@login_required
def attendance(request):
    if not hasattr(request.user, 'student'):
        messages.error(request, "Only students can view their attendance records.")
        return render(request, 'attendance/access_denied.html', status=403)

    student = request.user.student
    enrolled_classes = student.classes.all()
    lectures = Lecture.objects.filter(lecture_class__in=enrolled_classes).distinct()

    if not lectures:
        messages.info(request, "You are not enrolled in any lectures.")
        return render(request, 'attendance/student_attendance.html', {'lectures': []})

    lecture_data = []
    for lecture in lectures:
        lecture_days = lecture.days.all()
        if not lecture_days:
            continue

        today = date.today()
        date_range = [today - timedelta(days=x) for x in range(30)]
        lecture_dates = [
            d for d in date_range
            if any(day.name == d.strftime('%A') for day in lecture_days)
        ]

        attendance_records = Attendance.objects.filter(
            student=student,
            date__in=lecture_dates,
            lectures=lecture
        ).select_related('student')

        attendance_dict = {}
        for record in attendance_records:
            date_str = record.date.strftime("%Y-%m-%d")
            attendance_dict[date_str] = {
                'status': record.status,
                'is_makeup': record.is_makeup
            }

        lecture_data.append({
            'lecture': lecture,
            'lecture_dates': sorted(lecture_dates, reverse=True),
            'attendance_dict': attendance_dict,
        })

    context = {
        'lectures': lecture_data,
        'student': student,
    }
    return render(request, 'attendance/student_attendance.html', context)

@login_required
def lecture_list(request, lecture_id=None):
    user = request.user
    if not user.is_staff:
        return render(request, 'attendance/access_denied.html', status=403)

    lectures = Lecture.objects.filter(teacher=user).order_by("start_time")

    if lecture_id:
        lecture = get_object_or_404(Lecture, lecture_id=lecture_id, teacher=user)
        class_id = lecture.lecture_class.id if lecture.lecture_class else None
        if class_id:
            return redirect('mark_attendance', class_id=class_id)
        else:
            messages.error(request, "This lecture has no associated class.")
            return redirect('lecture_list')

    return render(request, 'attendance/lecture_list.html', {'lectures': lectures, 'user': user})

@login_required
def mark_attendance(request, class_id):
    if not request.user.is_staff:
        return render(request, 'attendance/access_denied.html', status=403)

    lecture = get_object_or_404(Lecture, teacher=request.user, lecture_class__id=class_id)
    class_obj = lecture.lecture_class
    students = class_obj.students.all().order_by('roll_no')

    lecture_days = lecture.days.all()
    today = date.today()
    date_range = [today - timedelta(days=x) for x in range(30)]
    lecture_dates = [
        d for d in date_range
        if any(day.name == d.strftime('%A') for day in lecture_days)
    ]

    attendance_records = Attendance.objects.filter(
        student__in=students,
        date__in=lecture_dates,
        lectures=lecture
    ).select_related('student')

    attendance_dict = {}
    for record in attendance_records:
        student_id = str(record.student_id)
        date_str = record.date.strftime("%Y-%m-%d")
        if student_id not in attendance_dict:
            attendance_dict[student_id] = {}
        attendance_dict[student_id][date_str] = {
            'status': record.status,
            'is_makeup': record.is_makeup
        }

    if request.method == 'POST':
        success = False
        for student in students:
            for lecture_date_str in request.POST:
                if lecture_date_str.startswith('attendance_'):
                    parts = lecture_date_str.split('_')
                    if len(parts) == 4 and parts[1] == str(student.id):
                        date_str = parts[2]
                        is_makeup = parts[3] == 'makeup'
                        status = request.POST[lecture_date_str]
                        if status in ['Present', 'Absent', 'Late']:
                            try:
                                lecture_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                                attendance, created = Attendance.objects.update_or_create(
                                    student=student,
                                    date=lecture_date,
                                    is_makeup=is_makeup,
                                    defaults={'status': status}
                                )
                                attendance.lectures.set([lecture])
                                success = True
                            except ValueError:
                                continue

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if success:
                return JsonResponse({'success': True, 'message': 'Attendance updated successfully!'})
            else:
                return JsonResponse({'success': False, 'message': 'No valid attendance data provided.'}, status=400)

        if success:
            messages.success(request, "Attendance updated successfully!")
        else:
            messages.error(request, "No attendance data was updated.")
        return redirect('mark_attendance', class_id=class_id)

    context = {
        'lecture': lecture,
        'students': students,
        'lecture_dates': lecture_dates,
        'attendance_dict': attendance_dict,
    }
    return render(request, 'attendance/attendance_mark.html', context)