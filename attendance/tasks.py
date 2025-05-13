from celery import shared_task
from django.utils import timezone
from django.core.files.base import ContentFile
from django.conf import settings
from attendance.models import Lecture, AttendanceRecord, Attendance, Student
from accounts.models import CustomUser
from PIL import Image, ImageDraw, ImageFont
import base64
import io
import torch
import pickle
import numpy as np
from facenet_pytorch import MTCNN, InceptionResnetV1
from scipy.spatial.distance import cosine
import datetime

mtcnn = MTCNN(image_size=160, margin=0, min_face_size=20, keep_all=True)
resnet = InceptionResnetV1(pretrained='vggface2').eval()

@shared_task
def process_face_recognition(image_data, user_id, lecture_id=None):
    try:
        # Decode the base64 image
        image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')

        # Get current time and day
        current_time = timezone.now().time()
        current_day = timezone.now().strftime('%A')
        today = timezone.now().date()

        # If lecture_id is provided, use it; otherwise, find matching lectures
        if lecture_id:
            lectures = Lecture.objects.filter(pk=lecture_id)
        else:
            lectures = Lecture.objects.filter(
                teacher_id=user_id,
                start_time__lte=current_time,
                end_time__gte=current_time,
                days__name=current_day
            )

        if not lectures.exists():
            return {
                'status': 'error',
                'message': 'No matching lecture found for the current time and day.'
            }

        lecture = lectures.first()  # Use the first matching lecture
        lecture_class = lecture.lecture_class
        if not lecture_class:
            return {
                'status': 'error',
                'message': 'No class associated with this lecture.'
            }

        # Get students in the class
        students = lecture_class.students.all()

        # Detect faces and get embeddings
        faces, _ = mtcnn.detect(image)
        img_cropped = mtcnn(image)

        recognized_users = []
        face_positions = []

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
                    if distance < min_distance and distance < 0.6:
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

                    # Mark attendance
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

        # Save annotated image
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return {
            'status': 'success',
            'recognized_users': recognized_users,
            'annotated_image': image_base64,
            'lecture_id': lecture.pk
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }