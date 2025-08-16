from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.http import JsonResponse
from .models import AttendanceRecord, Attendance, Lecture, Leave
from .forms import AttendanceFormSet, LeaveForm
from accounts.models import CustomUser, Student
from subjects.models import Semester, Class,Course
from accounts.decorators import teacher_required, student_required
import base64
import io
import torch
import pickle
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial.distance import cosine
from facenet_pytorch import MTCNN, InceptionResnetV1
from .tasks import update_attendance_on_leave_approval

mtcnn = MTCNN(image_size=160, margin=0, min_face_size=20, keep_all=True)
resnet = InceptionResnetV1(pretrained='vggface2').eval()


from functools import wraps
import json

mtcnn = MTCNN(image_size=160, margin=0, min_face_size=20, keep_all=True)
resnet = InceptionResnetV1(pretrained='vggface2').eval()

def authenticate_using_face(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')  # Redirect to login if not authenticated

        # Check if face authentication is already done in session
        if request.session.get('face_authenticated', False):
            return view_func(request, *args, **kwargs)

        if request.method == 'POST' and request.path.endswith('verify-face/'):
            return verify_face(request)  # Handle face verification

        # Render the webcam capture page
        return render(request, 'attendance/verify_face.html', {
            'next': request.path
        })
    return wrapper

@require_POST
def verify_face(request):
    try:
        data = json.loads(request.body)
        image_data = data.get('image')
        if not image_data:
            return JsonResponse({'status': 'error', 'message': 'No image provided'}, status=400)

        # Decode base64 image
        image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')

        # Detect and extract face
        faces, _ = mtcnn.detect(image)
        img_cropped = mtcnn(image)

        if img_cropped is None or faces is None or len(faces) != 1:
            return JsonResponse({'status': 'error', 'message': 'Exactly one face must be detected'}, status=400)

        # Generate embedding
        with torch.no_grad():
            embedding = resnet(img_cropped).detach().cpu().numpy().flatten()

        # Get user's stored face encoding
        user = request.user
        if not user.face_encoding:
            return JsonResponse({'status': 'error', 'message': 'No face encoding stored for user'}, status=400)

        stored_embedding = pickle.loads(user.face_encoding).flatten()
        distance = cosine(embedding, stored_embedding)

        # Threshold for face match
        if distance < 0.7:
            request.session['face_authenticated'] = True
            request.session.modified = True
            return JsonResponse({'status': 'success', 'message': 'Face verified', 'redirect': data.get('next', '/')})
        else:
            return JsonResponse({'status': 'error', 'message': 'Face does not match'}, status=401)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@student_required
def leave_request(request):
    student = Student.objects.get(id=request.user.id)
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
        student_class = Class.objects.filter(
            semester=student.semester,
            degree_level=student.degree_level,
            discipline=student.discipline,
            shift=student.shift,
            section=student.section
        ).first()
        if student_class:
            form.fields['lecture'].queryset = Lecture.objects.filter(
                lecture_class=student_class,
                status='active'
            )
            if not form.fields['lecture'].queryset.exists():
                messages.warning(request, "No active lectures available for your class.")
        else:
            form.fields['lecture'].queryset = Lecture.objects.none()
            messages.warning(request, "No class found matching your profile. Please contact the administrator.")
    return render(request, 'attendance/leave_request.html', {'form': form})

def leave_list(request):
    today = timezone.now().date()
    Leave.objects.filter(leave_date__lt=today, status='Pending').update(status='Declined')
    
    if request.user.is_superuser:
        leaves = Leave.objects.all().order_by('-created_at')
    elif request.user.is_teacher:
        leaves = Leave.objects.filter(lecture__teacher=request.user).order_by('-created_at')
    elif request.user.is_student:
        leaves = Leave.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'attendance/leave_list.html', {'leaves': leaves})

@teacher_required
def leave_approve(request, leave_id):
    leave = get_object_or_404(Leave, id=leave_id, lecture__teacher=request.user)
    leave.status = 'Approved'
    leave.save()
    messages.success(request, f"Leave request for {leave.user} approved.")
    update_attendance_on_leave_approval.delay(leave_id)
    return redirect('leave_list')

@teacher_required
def leave_decline(request, leave_id):
    leave = get_object_or_404(Leave, id=leave_id, lecture__teacher=request.user)
    leave.status = 'Declined'
    leave.save()
    messages.success(request, f"Leave request for {leave.user} declined.")
    return redirect('leave_list')

@teacher_required
def lecture_list(request, lecture_id=None):
    user = request.user
    lectures = Lecture.objects.filter(teacher=user, lecture_class__isnull=False, status='active').order_by("start_time")
    today = timezone.now().date()

    for lecture in lectures:
        lecture.has_attendance_record = AttendanceRecord.objects.filter(
            lecture=lecture,
            date=today,
            is_makeup_class=False
        ).exists()
        lecture.has_makeup_class_record = AttendanceRecord.objects.filter(
            lecture=lecture,
            date=today,
            is_makeup_class=True
        ).exists()

    if lecture_id:
        lecture = get_object_or_404(Lecture, lecture_id=lecture_id, teacher=user, status='active')
        class_id = lecture.lecture_class.id if lecture.lecture_class else None
        if class_id:
            return redirect('capture_face', lecture_id=lecture.lecture_id)
        else:
            messages.error(request, "This lecture has no associated class.")
            return redirect('lecture_list')

    return render(request, 'attendance/lecture_list.html', {
        'lectures': lectures,
        'user': user
    })

@teacher_required
def add_makeup_class(request, lecture_id):
    lecture = get_object_or_404(Lecture, pk=lecture_id)
    today = timezone.now().date()

    if AttendanceRecord.objects.filter(
        lecture=lecture,
        date=today,
        is_makeup_class=True
    ).exists():
        messages.error(request, "A makeup class for this lecture and date already exists.")
        return redirect('lecture_list')

    request.session['is_makeup_class'] = True
    request.session['lecture_id'] = lecture_id
    return redirect('capture_face', lecture_id=lecture_id)

def attendance_success(request):
    return render(request, 'attendance/success.html', {'message': 'Attendance marked successfully!'})
# capture_face view
@teacher_required
def capture_face(request, lecture_id):
    lecture = get_object_or_404(Lecture, pk=lecture_id)
    lecture_class = lecture.lecture_class
    if not lecture_class:
        messages.error(request, "This lecture has no associated class.")
        return redirect('lecture_list')

    students = lecture_class.students.all()
    is_makeup_class = request.session.get('is_makeup_class', False)

    if request.method == 'POST':
        image_files = request.FILES.getlist('image_files')
        if not image_files:
            messages.error(request, "Please upload at least one image.")
            return render(request, 'attendance/capture_face.html', {'lecture': lecture, 'is_makeup_class': is_makeup_class})

        all_recognized_users = []
        annotated_images = []
        total_faces_detected = 0  # Track total faces detected

        for image_file in image_files:
            image = Image.open(image_file).convert('RGB')

            # Handle orientation: Rotate image if needed
            try:
                exif = image._getexif()
                if exif:
                    orientation = exif.get(274, 1)
                    if orientation == 3:
                        image = image.rotate(180, expand=True)
                    elif orientation == 6:
                        image = image.rotate(270, expand=True)
                    elif orientation == 8:
                        image = image.rotate(90, expand=True)
            except:
                pass

            faces, _ = mtcnn.detect(image)
            img_cropped = mtcnn(image)

            face_positions = []
            recognized_users = []
            seen_students = set()

            if img_cropped is not None and faces is not None:
                total_faces_detected += len(faces)  # Count detected faces
                with torch.no_grad():
                    embeddings = resnet(img_cropped).detach().cpu().numpy()

                users = CustomUser.objects.filter(
                    id__in=students.values_list('id', flat=True),
                    face_encoding__isnull=False
                )

                detections = []
                for i, embedding in enumerate(embeddings):
                    embedding_np = embedding.flatten()
                    face_position = faces[i]

                    min_distance = float('inf')
                    recognized_user, recognized_student = None, None
                    for user in users:
                        stored_embedding = pickle.loads(user.face_encoding).flatten()
                        distance = cosine(embedding_np, stored_embedding)
                        if distance < min_distance:
                            min_distance = distance
                            recognized_user = user
                            recognized_student = students.get(id=user.id)

                    if min_distance < 0.7:
                        detections.append({
                            'user': recognized_user,
                            'student': recognized_student,
                            'distance': min_distance,
                            'position': face_position
                        })
                    else:
                        detections.append({
                            'user': None,
                            'student': None,
                            'distance': min_distance,
                            'position': face_position
                        })

                for detection in sorted(detections, key=lambda x: x['distance']):
                    face_position = detection['position']
                    if detection['user'] and detection['student']:
                        roll_no = detection['student'].roll_no
                        if roll_no not in seen_students:
                            seen_students.add(roll_no)
                            recognized_users.append({
                                'name': f"{detection['user'].first_name} {detection['user'].last_name}",
                                'email': detection['user'].email,
                                'roll_no': roll_no
                            })
                            face_positions.append({
                                'position': face_position,
                                'name': f"{detection['user'].first_name} {detection['user'].last_name}"
                            })
                        else:
                            face_positions.append({
                                'position': face_position,
                                'name': "Unknown"
                            })
                    else:
                        face_positions.append({
                            'position': face_position,
                            'name': "Unknown"
                        })

            if face_positions:
                draw = ImageDraw.Draw(image)
                try:
                    font = ImageFont.truetype("arial.ttf", 20)
                except:
                    font = ImageFont.load_default()

                for face in face_positions:
                    pos = face['position']
                    draw.rectangle([(pos[0], pos[1]), (pos[2], pos[3])], outline='red', width=2)
                    draw.text((pos[0], pos[1] - 25), face['name'], fill='red', font=font)

            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            annotated_images.append(image_base64)
            all_recognized_users.extend(recognized_users)

        seen = set()
        unique_recognized_users = []
        for user in all_recognized_users:
            if user['roll_no'] not in seen:
                unique_recognized_users.append(user)
                seen.add(user['roll_no'])

        request.session['recognized_users'] = unique_recognized_users
        request.session['annotated_images'] = annotated_images
        request.session['lecture_id'] = lecture_id
        request.session['is_makeup_class'] = is_makeup_class
        request.session['total_faces_detected'] = total_faces_detected  # Store in session

        if not unique_recognized_users:
            messages.warning(request, "No students were recognized. All students will be marked as absent unless manually updated.")

        is_makeup_class_int = 1 if is_makeup_class else 0
        return redirect('mark_attendance', lecture_id=lecture_id, is_makeup_class=is_makeup_class_int)

    return render(request, 'attendance/capture_face.html', {
        'lecture': lecture,
        'is_makeup_class': is_makeup_class
    })
@teacher_required
def mark_attendance(request, lecture_id, is_makeup_class=False):
    lecture = get_object_or_404(Lecture, pk=lecture_id)
    today = timezone.now().date()

    if AttendanceRecord.objects.filter(
        lecture=lecture,
        date=today,
        is_makeup_class=is_makeup_class
    ).exists():
        messages.error(request, "Attendance for this lecture and date has already been marked.")
        return redirect('lecture_list')

    students = lecture.lecture_class.students.all().order_by('roll_no')
    recognized_users = request.session.get('recognized_users', [])
    annotated_images = request.session.get('annotated_images', [])
    total_faces_detected = request.session.get('total_faces_detected', 0)  # Get from session

    recognized_roll_nos = [user['roll_no'] for user in recognized_users]

    record = AttendanceRecord.objects.create(
        lecture=lecture,
        date=today,
        is_makeup_class=is_makeup_class
    )

    for student in students:
        status = 'present' if student.roll_no in recognized_roll_nos else 'absent'
        Attendance.objects.create(
            student=student,
            attendance_record=record,
            attendance_status=status
        )

    # Clear session
    request.session.pop('recognized_users', None)
    request.session.pop('annotated_images', None)
    request.session.pop('lecture_id', None)
    request.session.pop('is_makeup_class', None)
    request.session.pop('total_faces_detected', None)

    messages.success(request, "Attendance marked successfully!")

    return render(request, 'attendance/mark_attendance.html', {
        'lecture': lecture,
        'date': today,
        'is_makeup_class': is_makeup_class,
        'annotated_images': annotated_images,
        'recognized_users': recognized_users,
        'attendance_marked': True,
        'total_faces_detected': total_faces_detected,
        'total_recognized': len(recognized_users),
    })

@authenticate_using_face
@teacher_required
def edit_attendance(request, lecture_id, attendance_record_id):
    lecture = get_object_or_404(Lecture, pk=lecture_id)
    record = get_object_or_404(AttendanceRecord, id=attendance_record_id, lecture=lecture)
    record_date = record.date

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
    else:
        formset = AttendanceFormSet(queryset=Attendance.objects.filter(attendance_record=record))

    return render(request, 'attendance/edit_attendance.html', {
        'formset': formset,
        'lecture': lecture,
        'date': record_date,
        'record': record,
    })

@student_required
def student_attendance(request):
    student = get_object_or_404(Student, id=request.user.id)
    current_semester = student.semester
    all_semesters = [current_semester] + list(Semester.objects.filter(name__lt=current_semester.name).order_by('-name'))

    degree_completed = False
    if not all_semesters or current_semester.name == "1st Semester":  # Assuming 1st is the last if no progression
        degree_completed = True
        return render(request, 'attendance/student_attendance.html', {
            'degree_completed': degree_completed,
        })

    attendance_data = {}
    for semester in all_semesters:
        courses = Course.objects.filter(
            semester=semester,
            degree_level=student.degree_level,
            discipline=student.discipline
        )
        attendance_data[semester.name] = courses

    return render(request, 'attendance/student_attendance.html', {
        'semesters': all_semesters,
        'attendance_data': attendance_data,
        'degree_completed': degree_completed,
    })

@student_required
def attendance_details(request, semester_id, course_id):
    student = get_object_or_404(Student, id=request.user.id)
    semester = get_object_or_404(Semester, id=semester_id)
    course = get_object_or_404(Course, id=course_id)

    lectures = Lecture.objects.filter(
        course=course,
        lecture_class__degree_level=student.degree_level,
        lecture_class__discipline=student.discipline,
        lecture_class__section=student.section,
        lecture_class__shift=student.shift
    )
    attendance_records = Attendance.objects.filter(
        student=student,
        attendance_record__lecture__in=lectures
    ).select_related('attendance_record').order_by('-attendance_record__date')

    return render(request, 'attendance/attendance_details.html', {
        'semester': semester,
        'course': course,
        'attendance_records': attendance_records,
    })