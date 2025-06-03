from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
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

        recognized_users = []
        face_positions = []
        final_image = None

        for image_file in image_files:
            image = Image.open(image_file).convert('RGB')
            faces, _ = mtcnn.detect(image)
            img_cropped = mtcnn(image)

            if faces is not None:
                print(f"Detected {len(faces)} faces in image")
            else:
                print("No faces detected in image")
                messages.warning(request, "No faces detected in the uploaded image(s).")

            if img_cropped is not None:
                with torch.no_grad():
                    embeddings = resnet(img_cropped).detach().cpu().numpy()

                users = CustomUser.objects.filter(
                    id__in=students.values_list('id', flat=True),
                    face_encoding__isnull=False
                )

                print(f"Found {users.count()} users with face encodings")

                for i, embedding in enumerate(embeddings):
                    embedding_np = embedding.flatten()
                    face_position = faces[i]

                    min_distance = float('inf')
                    recognized_user = None
                    recognized_student = None
                    for user in users:
                        stored_embedding = pickle.loads(user.face_encoding).flatten()
                        distance = cosine(embedding_np, stored_embedding)
                        if distance < min_distance and distance < 0.7:
                            min_distance = distance
                            recognized_user = user
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
                        print(f"Recognized user: {recognized_user.first_name} {recognized_user.last_name} (Roll: {recognized_student.roll_no})")

            final_image = image

        if final_image and face_positions:
            draw = ImageDraw.Draw(final_image)
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

            buffer = io.BytesIO()
            final_image.save(buffer, format="JPEG")
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        else:
            image_base64 = ''
            messages.warning(request, "No recognized faces to annotate.")

        seen = set()
        unique_recognized_users = []
        for user in recognized_users:
            if user['roll_no'] not in seen:
                unique_recognized_users.append(user)
                seen.add(user['roll_no'])

        print(f"Final recognized users: {unique_recognized_users}")

        request.session['recognized_users'] = unique_recognized_users
        request.session['annotated_image'] = image_base64
        request.session['lecture_id'] = lecture_id
        request.session['is_makeup_class'] = is_makeup_class

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
    annotated_image = request.session.get('annotated_image', '')

    print(f" fungerar users in mark_attendance: {recognized_users}")

    recognized_roll_nos = [user['roll_no'] for user in recognized_users]
    print(f"Recognized roll numbers: {recognized_roll_nos}")
    student_roll_nos = [student.roll_no for student in students]
    print(f"All student roll numbers: {student_roll_nos}")

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

    attendance_entries = Attendance.objects.filter(attendance_record=record)
    for entry in attendance_entries:
        print(f"Student {entry.student.roll_no}: {entry.attendance_status}")

    request.session.pop('recognized_users', None)
    request.session.pop('annotated_image', None)
    request.session.pop('lecture_id', None)
    request.session.pop('is_makeup_class', None)

    student_dict = {student.id: student for student in students}

    messages.success(request, "Attendance marked successfully!")

    return render(request, 'attendance/mark_attendance.html', {
        'lecture': lecture,
        'date': today,
        'is_makeup_class': is_makeup_class,
        'annotated_image': annotated_image,
        'student_dict': student_dict,
        'recognized_users': recognized_users,
        'attendance_marked': True,
    })

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
        status__in=['active', 'ended'],
        lecture_class__semester=semester,
        lecture_class__degree_level=student.degree_level,
        lecture_class__discipline=student.discipline,
        lecture_class__section=student.section,
        lecture_class__shift=student.shift
    )
    attendance_records = Attendance.objects.filter(
        student=student,
        attendance_record__lecture__in=lectures
    ).select_related('attendance_record')

    return render(request, 'attendance/attendance_details.html', {
        'semester': semester,
        'course': course,
        'attendance_records': attendance_records,
    })