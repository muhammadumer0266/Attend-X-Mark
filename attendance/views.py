from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Leave, Lecture, Day, Attendance, CapturedFace
from .forms import LeaveForm, AttendanceFormSet
from django.contrib import messages
from accounts.models import Student, CustomUser
from django.core.files.base import ContentFile
import face_recognition
import base64
import os
import json
from django.conf import settings
from django.utils import timezone
from subjects.models import Class
from django.core.exceptions import ValidationError

@login_required
def leave_request(request):
    if request.method == 'POST':
        form = LeaveForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.user = request.user
            leave.save()
            messages.success(request, "Leave request submitted successfully.")
            return redirect('leave_list')
        else:
            messages.error(request, "Please correct the errors below.")
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
    messages.success(request, f"Leave request for {leave.user} approved.")
    return redirect('leave_list')

@login_required
def leave_decline(request, leave_id):
    leave = get_object_or_404(Leave, id=leave_id)
    leave.status = 'Declined'
    leave.save()
    messages.success(request, f"Leave request for {leave.user} declined.")
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
def lecture_list(request, lecture_id=None):
    user = request.user
    if not user.is_staff:
        return render(request, 'attendance/access_denied.html', status=403)

    lectures = Lecture.objects.filter(teacher=user, lecture_class__isnull=False).order_by("start_time")

    if lecture_id:
        lecture = get_object_or_404(Lecture, lecture_id=lecture_id, teacher=user)
        class_id = lecture.lecture_class.id if lecture.lecture_class else None
        if class_id:
            return redirect('mark_attendance', lecture_id=lecture.lecture_id, class_id=class_id)
        else:
            messages.error(request, "This lecture has no associated class.")
            return redirect('lecture_list')

    return render(request, 'attendance/lecture_list.html', {'lectures': lectures, 'user': user})
@login_required
def mark_attendance(request, lecture_id, class_id):
    if not request.user.is_staff:
        return render(request, 'attendance/access_denied.html', status=403)

    lecture = get_object_or_404(Lecture, lecture_id=lecture_id, teacher=request.user)
    lecture_class = get_object_or_404(Class, id=class_id)
    
    if lecture.lecture_class != lecture_class:
        messages.error(request, "This lecture does not belong to the specified class.")
        return redirect('lecture_list')

    students = lecture_class.students.all()
    print("Students:", list(students))  # Debug
    
    if not students.exists():
        messages.warning(request, "No students are enrolled in this class.")
        return redirect('lecture_list')

    today = timezone.now().date()
    current_day = today.strftime('%A')
    is_lecture_day = lecture.days.filter(name=current_day).exists()
    is_makeup = request.GET.get('is_makeup', 'False') == 'True'

    existing_attendance = Attendance.objects.filter(
        lecture=lecture,
        date=today,
        is_makeup=is_makeup
    ).exists()

    if existing_attendance:
        messages.warning(request, f"Attendance for this lecture on {today} {'(Makeup)' if is_makeup else ''} has already been marked.")
        return redirect('lecture_list')

    # Create initial data for the formset
    initial_data = [{'student': student.id, 'status': 'Absent'} for student in students]

    if request.method == 'POST':
        formset = AttendanceFormSet(
            request.POST,
            queryset=Attendance.objects.none(),
            initial=initial_data,
            extra=len(students)  # Ensure the formset creates a form for each student
        )
        print("POST Formset Forms:", len(formset.forms))  # Debug
        
        if formset.is_valid():
            for form in formset:
                attendance = Attendance(
                    lecture=lecture,
                    student=students[int(form.cleaned_data['student'])],  # Map back to student
                    date=today,
                    is_makeup=is_makeup,
                    status=form.cleaned_data['status']
                )
                try:
                    attendance.clean()
                    attendance.save()
                except ValidationError as e:
                    messages.error(request, f"Error for student: {str(e)}")
                    formset_students = list(zip(formset.forms, students))
                    return render(request, 'attendance/mark_attendance.html', {
                        'formset': formset,
                        'lecture': lecture,
                        'lecture_class': lecture_class,
                        'formset_students': formset_students,
                        'is_makeup': is_makeup,
                        'is_lecture_day': is_lecture_day,
                        'today': today,
                    })
            messages.success(request, "Attendance marked successfully.")
            return redirect('lecture_list')
        else:
            messages.error(request, "Please correct the errors below.")
            print("Formset Errors:", formset.errors)  # Debug
    else:
        formset = AttendanceFormSet(
            queryset=Attendance.objects.none(),
            initial=initial_data,
            extra=len(students)  # Ensure the formset creates a form for each student
        )
        print("GET Formset Forms:", len(formset.forms))  # Debug

    formset_students = list(zip(formset.forms, students))
    print("Formset Students:", formset_students)  # Debug

    context = {
        'formset': formset,
        'lecture': lecture,
        'lecture_class': lecture_class,
        'formset_students': formset_students,
        'is_makeup': is_makeup,
        'is_lecture_day': is_lecture_day,
        'today': today,
    }
    return render(request, 'attendance/mark_attendance.html', context)