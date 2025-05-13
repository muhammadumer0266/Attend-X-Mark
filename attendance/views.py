from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import AttendanceRecord, Attendance, Lecture, Leave
from .forms import AttendanceFormSet, LeaveForm

from accounts.models import CustomUser

import base64
import io
import torch
import pickle
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial.distance import cosine
from facenet_pytorch import MTCNN, InceptionResnetV1


mtcnn = MTCNN(image_size=160, margin=0, min_face_size=20, keep_all=True)
resnet = InceptionResnetV1(pretrained='vggface2').eval()

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
def lecture_list(request, lecture_id=None):
    user = request.user
    if not user.is_staff:
        return render(request, 'attendance/access_denied.html', status=403)

    lectures = Lecture.objects.filter(teacher=user, lecture_class__isnull=False).order_by("start_time")
    today = timezone.now().date()

    # Add has_attendance_record attribute to each lecture
    for lecture in lectures:
        lecture.has_attendance_record = AttendanceRecord.objects.filter(
            lecture=lecture, date=today, is_makeup_class=False
        ).exists()

    if lecture_id:
        lecture = get_object_or_404(Lecture, lecture_id=lecture_id, teacher=user)
        class_id = lecture.lecture_class.id if lecture.lecture_class else None
        if class_id:
            return redirect('mark_attendance', lecture_id=lecture.lecture_id, class_id=class_id)
        else:
            messages.error(request, "This lecture has no associated class.")
            return redirect('lecture_list')

    return render(request, 'attendance/lecture_list.html', {'lectures': lectures, 'user': user})

def mark_attendance(request, lecture_id, is_makeup_class=False):
    lecture = get_object_or_404(Lecture, pk=lecture_id)
    today = timezone.now().date()

    # Try to get or create attendance record
    record, created = AttendanceRecord.objects.get_or_create(
        lecture=lecture,
        date=today,
        is_makeup_class=is_makeup_class,
        defaults={'is_makeup_class': is_makeup_class}
    )

    # Only allow students from the class
    students = lecture.lecture_class.students.all().order_by('roll_no')

    if request.method == 'POST':
        formset = AttendanceFormSet(request.POST, queryset=Attendance.objects.filter(attendance_record=record))
        if formset.is_valid():
            for form in formset:
                if form.has_changed():  # Only save if the form has changes
                    attendance = form.save(commit=False)
                    attendance.attendance_record = record
                    attendance.save()
            return redirect('attendance_success')  # Redirect to success page
    else:
        # Pre-fill data if not exists
        existing_attendance = Attendance.objects.filter(attendance_record=record)
        if not existing_attendance.exists():
            for student in students:
                Attendance.objects.get_or_create(
                    attendance_record=record,
                    student=student,
                    defaults={'attendance_status': 'absent'}  # Default status
                )

        formset = AttendanceFormSet(queryset=Attendance.objects.filter(attendance_record=record))

    return render(request, 'attendance/mark_attendance.html', {
        'formset': formset,
        'lecture': lecture,
        'date': today,
        'record': record,
        'is_makeup_class': is_makeup_class
    })

@login_required
def add_makeup_class(request, lecture_id):
    lecture = get_object_or_404(Lecture, pk=lecture_id)
    today = timezone.now().date()

    # Check if a makeup class record already exists for today
    if AttendanceRecord.objects.filter(
        lecture=lecture,
        date=today,
        is_makeup_class=True
    ).exists():
        messages.error(request, "A makeup class for this lecture and date already exists.")
        return redirect('lecture_list')

    return mark_attendance(request, lecture_id, is_makeup_class=True)

def attendance_success(request):
    return render(request, 'attendance/success.html', {'message': 'Attendance marked successfully!'})

@login_required
def capture_face(request, lecture_id):
    if not request.user.is_teacher:
        return render(request, 'attendance/access_denied.html', status=403)

    # Get the lecture and associated class
    lecture = get_object_or_404(Lecture, pk=lecture_id)
    lecture_class = lecture.lecture_class
    if not lecture_class:
        messages.error(request, "This lecture has no associated class.")
        return redirect('lecture_list')

    # Get students in the class
    students = lecture_class.students.all()

    if request.method == 'POST':
        image_data = request.POST.get('image_data')
        uploaded_file = request.FILES.get('image_file')

        if not image_data and not uploaded_file:
            messages.error(request, "Please capture or upload an image.")
            return render(request, 'attendance/capture_face.html', {'lecture': lecture})

        # Process the image (either from camera or upload)
        if image_data:
            image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        else:
            image = Image.open(uploaded_file).convert('RGB')

        # Detect faces and get embeddings
        faces, _ = mtcnn.detect(image)
        img_cropped = mtcnn(image)

        recognized_users = []
        face_positions = []
        today = timezone.now().date()

        # Create or get attendance record
        record, created = AttendanceRecord.objects.get_or_create(
            lecture=lecture,
            date=today,
            is_makeup_class=False,
            defaults={'is_makeup_class': False}
        )

        if img_cropped is not None:
            # Generate embeddings for all detected faces
            with torch.no_grad():
                embeddings = resnet(img_cropped).detach().cpu().numpy()

            # Filter users to only students in the class with face encodings
            users = CustomUser.objects.filter(
                id__in=students.values_list('id', flat=True),
                face_encoding__isnull=False
            )

            # For each detected face
            for i, embedding in enumerate(embeddings):
                embedding_np = embedding
                face_position = faces[i]

                # Compare with stored embeddings
                min_distance = float('inf')
                recognized_user = None
                recognized_student = None
                for user in users:
                    stored_embedding = pickle.loads(user.face_encoding).flatten()
                    distance = cosine(embedding_np, stored_embedding)
                    if distance < min_distance and distance < 0.6:  # Tightened threshold for better accuracy
                        min_distance = distance
                        recognized_user = user
                        # Get the corresponding Student object
                        recognized_student = students.get(id=user.id)

                if recognized_user and recognized_student:
                    recognized_users.append({
                        'name': f"{recognized_user.first_name} {recognized_user.last_name}",
                        'email': recognized_user.email,
                        'roll_no': recognized_student.roll_no
                    })
                    face_positions.append({
                        'position': face_position,
                        'name': f"{recognized_user.first_name} {recognized_user.last_name}"
                    })

                    # Automatically mark attendance as present
                    Attendance.objects.update_or_create(
                        attendance_record=record,
                        student=recognized_student,
                        defaults={'attendance_status': 'present'}
                    )

        # Draw rectangles and names on the image
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()

        for face in face_positions:
            position = face['position']
            name = face['name']
            draw.rectangle(
                [(position[0], position[1]), (position[2], position[3])],
                outline='red',
                width=2
            )
            draw.text(
                (position[0], position[1] - 25),
                name,
                fill='red',
                font=font
            )

        # Save the annotated image to a BytesIO buffer and encode as base64
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        # Store results in session
        request.session['recognized_users'] = recognized_users
        request.session['annotated_image'] = image_base64
        request.session['lecture_id'] = lecture_id

        return redirect('capture_success')

    return render(request, 'attendance/capture_face.html', {'lecture': lecture})

@login_required
def capture_success(request):
    if not request.user.is_teacher:
        return render(request, 'attendance/access_denied.html', status=403)

    recognized_users = request.session.get('recognized_users', [])
    annotated_image = request.session.get('annotated_image', '')
    lecture_id = request.session.get('lecture_id')

    if not recognized_users or not annotated_image or not lecture_id:
        messages.error(request, "No face capture data found. Please capture an image first.")
        return redirect('lecture_list')

    lecture = get_object_or_404(Lecture, pk=lecture_id)

    context = {
        'recognized_users': recognized_users,
        'annotated_image': annotated_image,
        'lecture': lecture,
    }
    return render(request, 'attendance/capture_success.html', context)

@login_required
def edit_attendance(request, lecture_id, attendance_record_id):
    lecture = get_object_or_404(Lecture, pk=lecture_id)
    if not request.user.is_teacher or lecture.teacher != request.user:
        return render(request, 'attendance/access_denied.html', status=403)

    # Get the attendance record using the ID
    record = get_object_or_404(AttendanceRecord, id=attendance_record_id, lecture=lecture)
    record_date = record.date  # For display purposes

    # Get all students in the lecture's class
    students = lecture.lecture_class.students.all().order_by('roll_no')

    if request.method == 'POST':
        formset = AttendanceFormSet(request.POST, queryset=Attendance.objects.filter(attendance_record=record))
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.attendance_record = record
                instance.save()
            messages.success(request, "Attendance updated successfully.")
            return redirect('student_attendance_report', lecture_id=lecture_id)
        else:
            messages.error(request, "Please correct the errors below.")
            for form in formset:
                if form.errors:
                    print(form.errors)  # Debug: Print errors to console
    else:
        # Ensure attendance records exist for all students
        existing_attendance = Attendance.objects.filter(attendance_record=record)
        if not existing_attendance.exists():
            for student in students:
                Attendance.objects.get_or_create(
                    attendance_record=record,
                    student=student,
                    defaults={'attendance_status': 'absent'}
                )
        formset = AttendanceFormSet(queryset=Attendance.objects.filter(attendance_record=record))

    return render(request, 'attendance/edit_attendance.html', {
        'formset': formset,
        'lecture': lecture,
        'date': record_date,
        'record': record,
    })