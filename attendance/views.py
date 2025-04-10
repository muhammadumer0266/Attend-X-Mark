from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Leave
from .forms import LeaveForm
from django.contrib import messages
from .models import Lecture


@login_required
def leave_request(request):
    if request.method == 'POST':
        form = LeaveForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.user = request.user  # Associate logged-in user
            leave.save()
            return redirect('leave_list')  # Redirect to leave list after submission
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
from django.shortcuts import render, redirect
from django.core.files.base import ContentFile
from django.conf import settings
import face_recognition
import base64
import os
import json
from .models import CapturedFace
from accounts.models import CustomUser

def capture_face(request):
    if request.method == 'POST':
        image_data_json = request.POST.get('image_data[]')
        if image_data_json:
            image_data_list = json.loads(image_data_json)  # Parse JSON string to list
            captured_face_ids = []

            # Save all images
            for image_data in image_data_list:
                format, imgstr = image_data.split(';base64,')
                ext = format.split('/')[-1]
                image_file = ContentFile(base64.b64decode(imgstr), name=f'captured_image_{len(captured_face_ids) + 1}.{ext}')
                captured_face = CapturedFace(user=request.user, image=image_file)
                captured_face.save()
                captured_face_ids.append(captured_face.id)

            # Redirect to success page with all captured face IDs
            return redirect('capture_success', captured_face_ids=','.join(map(str, captured_face_ids)))
    
    return render(request, 'attendance/capture_face.html')

from django.shortcuts import render, redirect
from django.core.files.base import ContentFile
from django.conf import settings
import face_recognition
import base64
import os
import json
from .models import CapturedFace
from accounts.models import CustomUser

def capture_success(request, captured_face_ids):
    try:
        face_ids = [int(id) for id in captured_face_ids.split(',')]
        captured_faces = CapturedFace.objects.filter(id__in=face_ids)
        
        # Process all captured images
        total_faces_detected = 0
        matched_students = set()  # To track unique matched student usernames
        captured_images_info = []

        # Collect all face encodings from captured images
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

        # Compare with profile pictures of all users
        if all_uploaded_encodings:
            all_users = CustomUser.objects.exclude(profile_picture='profile_pics/defpic.png')  # Exclude users with default pic
            for user in all_users:
                if not user.is_student:  # Only match students
                    continue
                    
                profile_pic_path = os.path.join(settings.MEDIA_ROOT, user.profile_picture.name)
                if os.path.exists(profile_pic_path):  # Ensure the file exists
                    known_image = face_recognition.load_image_file(profile_pic_path)
                    known_encodings = face_recognition.face_encodings(known_image)
                    
                    if known_encodings:  # Ensure at least one face is detected in the profile pic
                        for uploaded_encoding in all_uploaded_encodings:
                            matches = face_recognition.compare_faces([known_encodings[0]], uploaded_encoding)
                            if matches[0]:
                                distance = face_recognition.face_distance([known_encodings[0]], uploaded_encoding)[0]
                                # Use a threshold for matching (e.g., 0.6 is a common default)
                                if distance < 0.6:
                                    matched_students.add(user.username)
                                    break  # Move to next user after first match

        context = {
            'matched_students': list(matched_students),  # Convert set to list for template
            'total_faces_detected': total_faces_detected,
            'captured_images_info': captured_images_info,
        }
        return render(request, 'attendance/capture_success.html', context)

    except CapturedFace.DoesNotExist:
        return render(request, 'attendance/capture_face.html', {'error': 'Captured face not found'})
    except Exception as e:
        return render(request, 'attendance/capture_face.html', {'error': f'An error occurred: {str(e)}'})
        

def attendance(request):
    return render(request, 'attendance/attendance.html')


@login_required
def lecture_list(request, lecture_id=None):
    user = request.user
    if not user.is_staff:
        return render(request, 'attendance/access_denied.html', status=403)

    lectures = Lecture.objects.filter(teacher=user).order_by("start_time")

    # If lecture_id is provided (e.g., via a URL or POST), redirect to mark_attendance
    if lecture_id:
        lecture = get_object_or_404(Lecture, lecture_id=lecture_id, teacher=user)
        class_id = lecture.lecture_class.id if lecture.lecture_class else None
        if class_id:
            return redirect('mark_attendance', class_id=class_id)
        else:
            messages.error(request, "This lecture has no associated class.")
            return redirect('lecture_list')

    return render(request, 'attendance/lecture_list.html', {'lectures': lectures, 'user': user})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Lecture, Attendance, Day
from accounts.models import Student
from .forms import AttendanceFormSet
from django.contrib import messages
from datetime import date, timedelta

@login_required
def mark_attendance(request, class_id):
    # Ensure only teachers can access this
    if not request.user.is_staff:
        return render(request, 'attendance/access_denied.html', status=403)

    # Get the lecture based on the teacher's lectures and class
    lecture = get_object_or_404(Lecture, teacher=request.user, lecture_class__id=class_id)
    class_obj = lecture.lecture_class
    students = class_obj.students.all()

    # Get the days the lecture occurs
    lecture_days = lecture.days.all()

    # Generate a date range (e.g., last 30 days) or use semester dates
    today = date.today()
    date_range = [today - timedelta(days=x) for x in range(30)]  # Adjust range as needed
    date_range.reverse()  # Chronological order

    # Filter dates to only include lecture days
    lecture_dates = [
        d for d in date_range
        if any(day.name == d.strftime('%A') for day in lecture_days)
    ]

    # Fetch existing attendance records
    attendance_records = Attendance.objects.filter(
        student__in=students,
        date__in=lecture_dates,
        lectures=lecture
    ).select_related('student')

    # Create a dictionary of attendance statuses: {student_id: {date: status}}
    attendance_dict = {}
    for record in attendance_records:
        if record.student_id not in attendance_dict:
            attendance_dict[record.student_id] = {}
        attendance_dict[record.student_id][record.date] = record.status

    if request.method == 'POST':
        # Handle form submission
        for student in students:
            for lecture_date in lecture_dates:
                status_key = f'attendance_{student.id}_{lecture_date.strftime("%Y-%m-%d")}'
                if status_key in request.POST:
                    status = request.POST[status_key]
                    if status in ['Present', 'Absent', 'Late']:
                        # Update or create attendance record
                        attendance, created = Attendance.objects.update_or_create(
                            student=student,
                            date=lecture_date,
                            lectures=lecture,
                            defaults={'status': status}
                        )
        messages.success(request, "Attendance updated successfully!")
        return redirect('mark_attendance', class_id=class_id)

    # Prepare context for the template
    context = {
        'lecture': lecture,
        'students': students,
        'lecture_dates': lecture_dates,
        'attendance_dict': attendance_dict,
    }
    return render(request, 'attendance/attendance_mark.html', context)