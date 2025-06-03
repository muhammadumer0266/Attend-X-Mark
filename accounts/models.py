from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from subjects.models import DegreeLevel, Discipline, Semester, Department
from phonenumber_field.modelfields import PhoneNumberField
from django.utils.translation import gettext_lazy as _
import pickle
from PIL import Image
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch
from django.conf import settings
import threading
import asyncio
import aiosmtplib
from email.mime.text import MIMEText

# Initialize MTCNN and InceptionResnetV1 for face detection and embedding
mtcnn = MTCNN(image_size=160, margin=0, min_face_size=20)
resnet = InceptionResnetV1(pretrained='vggface2').eval()

# Custom Manager for User
class CustomUserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field is required')
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, first_name, last_name, password, **extra_fields)

# Custom User Model
class CustomUser(AbstractBaseUser, PermissionsMixin):
    profile_picture = models.ImageField(upload_to='profile_pics/', default='profile_pics/defpic.png')
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
    )

    # User details
    username = models.CharField(max_length=150, unique=True, blank=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    contact_number = PhoneNumberField(_("Contact Number"), region="PK", blank=True, null=True)
    face_encoding = models.BinaryField(blank=True, null=True)

    # Link to Semester model in subjects app
    is_teacher = models.BooleanField(default=False)
    is_student = models.BooleanField(default=False)

    # Permissions
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)  # Default to False, set based on role

    # Custom User Manager
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email

# Signal to automatically set username from email
@receiver(pre_save, sender=CustomUser)
def set_username_from_email(sender, instance, **kwargs):
    if instance.email and not instance.username:
        instance.username = instance.email.split('@')[0]

# Signal to generate face encoding from profile picture
@receiver(post_save, sender=CustomUser)
def generate_face_encoding(sender, instance, created, **kwargs):
    if instance.profile_picture and instance.profile_picture != 'profile_pics/defpic.png':
        try:
            # Open the profile picture
            img = Image.open(instance.profile_picture.path).convert('RGB')
            
            # Detect face and get embedding
            img_cropped = mtcnn(img)
            if img_cropped is not None:
                img_cropped = img_cropped.unsqueeze(0)  # Add batch dimension
                with torch.no_grad():
                    embedding = resnet(img_cropped).detach().cpu().numpy()
                
                # Serialize the embedding using pickle
                embedding_bytes = pickle.dumps(embedding)
                
                # Disconnect the signal to prevent recursion
                post_save.disconnect(generate_face_encoding, sender=CustomUser)
                try:
                    instance.face_encoding = embedding_bytes
                    instance.save(update_fields=['face_encoding'])
                finally:
                    # Reconnect the signal
                    post_save.connect(generate_face_encoding, sender=CustomUser)
            else:
                # No face detected, clear the face_encoding
                post_save.disconnect(generate_face_encoding, sender=CustomUser)
                try:
                    instance.face_encoding = None
                    instance.save(update_fields=['face_encoding'])
                finally:
                    post_save.connect(generate_face_encoding, sender=CustomUser)
        except Exception as e:
            print(f"Error generating face encoding for {instance.email}: {str(e)}")
            post_save.disconnect(generate_face_encoding, sender=CustomUser)
            try:
                instance.face_encoding = None
                instance.save(update_fields=['face_encoding'])
            finally:
                post_save.connect(generate_face_encoding, sender=CustomUser)

# Signal to create/update Teacher or Student after CustomUser is saved
@receiver(post_save, sender=CustomUser)
def create_teacher_or_student(sender, instance, created, **kwargs):
    # Ensure only one of is_teacher or is_student is True
    if instance.is_teacher and instance.is_student:
        raise ValueError("A user cannot be both a teacher and a student.")

    # Disconnect signals to prevent recursion
    post_save.disconnect(create_teacher_or_student, sender=CustomUser)
    post_save.disconnect(generate_face_encoding, sender=CustomUser)
    try:
        # Handle Teacher creation/update
        if instance.is_teacher:
            teacher, _ = Teacher.objects.update_or_create(
                id=instance.id,
                defaults={
                    'profile_picture': instance.profile_picture,
                    'status': instance.status,
                    'username': instance.username,
                    'first_name': instance.first_name,
                    'last_name': instance.last_name,
                    'email': instance.email,
                    'password': instance.password,
                    'face_encoding': instance.face_encoding,
                    'is_teacher': True,
                    'is_student': False,
                    'is_active': instance.is_active,
                    'is_staff': True,  # Teachers are staff
                }
            )
            # Update the CustomUser instance with the teacher's password (hashed)
            instance.password = teacher.password
            instance.save(update_fields=['password'])
        # Handle Student creation/update
        elif instance.is_student:
            student, _ = Student.objects.update_or_create(
                id=instance.id,
                defaults={
                    'profile_picture': instance.profile_picture,
                    'status': instance.status,
                    'username': instance.username,
                    'first_name': instance.first_name,
                    'last_name': instance.last_name,
                    'email': instance.email,
                    'password': instance.password,
                    'face_encoding': instance.face_encoding,
                    'is_teacher': False,
                    'is_student': True,
                    'is_active': instance.is_active,
                    'is_staff': False,  # Students are not staff
                }
            )
            # Update the CustomUser instance with the student's password (hashed)
            instance.password = student.password
            instance.save(update_fields=['password'])
    finally:
        # Reconnect the signals
        post_save.connect(create_teacher_or_student, sender=CustomUser)
        post_save.connect(generate_face_encoding, sender=CustomUser)



# Asynchronous function to send email using aiosmtplib
async def send_email_async(subject, message, from_email, recipient_list):
    try:
        # Create the email message
        email_message = MIMEText(message)
        email_message['Subject'] = subject
        email_message['From'] = from_email
        email_message['To'] = ', '.join(recipient_list)

        # Connect to the SMTP server and send the email
        smtp_client = aiosmtplib.SMTP(
            hostname=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            use_tls=settings.EMAIL_USE_TLS,
        )
        await smtp_client.connect()
        await smtp_client.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        await smtp_client.send_message(email_message)
        await smtp_client.quit()
    except Exception as e:
        print(f"Error sending async email to {recipient_list}: {str(e)}")

# Function to run the async email sending in a new event loop
def run_async_email(subject, message, from_email, recipient_list):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(send_email_async(subject, message, from_email, recipient_list))
    finally:
        loop.close()

# Signal to send email when user is activated
@receiver(post_save, sender=CustomUser)
def notify_user_on_approval(sender, instance, created, **kwargs):
    # Skip if this is a new user creation (we don't want to notify on creation)
    if created:
        return

    # Check if the user was updated, status changed to 'approved', and is_active changed to True
    try:
        # Fetch the previous state of the instance
        old_instance = CustomUser.objects.get(pk=instance.pk)
        # If status changed to 'approved' and is_active changed from False to True
        if (old_instance.status != 'approved' and instance.status == 'approved' and
            not old_instance.is_active and instance.is_active):
            subject = 'Account Activated - AttendXMark'
            message = (
                f'Hello {instance.first_name} {instance.last_name},\n\n'
                'Congratulations! Your account with AttendXMark has been activated by the administrator.\n'
                'You can now log in to your account using your email and password.\n\n'
                'Best regards,\nThe AttendXMark Team'
            )
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [instance.email]

            # Offload the email sending to a separate thread to run asynchronously
            threading.Thread(
                target=run_async_email,
                args=(subject, message, from_email, recipient_list),
            ).start()
    except CustomUser.DoesNotExist:
        # This shouldn't happen, but handle it just in case
        pass

# Teacher Model
class Teacher(CustomUser):
    DESIGNATION_CHOICES = (
        ('hod', 'HOD'),
        ('lecturer', 'Lecturer'),
        ('associate_professor', 'Associate Professor'),
        ('assistant_professor', 'Assistant Professor'),
        ('lecturer_associate', 'Lecturer Associate'),
        ('lecturer_assistant', 'Lecturer Assistant'),
        ('cti', 'CTI'),
    )
    
    designation = models.CharField(
        max_length=20,
        choices=DESIGNATION_CHOICES,
        default=None,
        blank=True,
        null=True
    )
    office_room_number = models.CharField(max_length=50, blank=True, null=True)
    specialization = models.CharField(max_length=255, blank=True, null=True)
    joining_date = models.DateField(blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    courses = models.ManyToManyField('subjects.Course', blank=True)
    
    class Meta:
        verbose_name = "Teacher"
        verbose_name_plural = "Teachers"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

# Student Model
class Student(CustomUser):
    roll_no = models.CharField(max_length=20, unique=True, null=True, blank=True)
    degree_level = models.ForeignKey(DegreeLevel, on_delete=models.SET_NULL, null=True, blank=True)
    discipline = models.ForeignKey(Discipline, on_delete=models.SET_NULL, null=True, blank=True)
    semester = models.ForeignKey(Semester, on_delete=models.SET_NULL, null=True, blank=True)
    shift = models.ForeignKey('subjects.Shift', on_delete=models.SET_NULL, null=True, blank=True)
    section = models.ForeignKey('subjects.Section', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Student"
        verbose_name_plural = "Students"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.roll_no or self.email})"
    

from django.db import models
from django.contrib.auth import get_user_model

CustomUser = get_user_model()

class PasswordResetOTP(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"OTP for {self.user.username} - {self.otp}"
    
# Add this new model to your existing models.py file

class PersonalInfoOTP(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    email = models.EmailField()  # The email where OTP was sent
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Personal Info OTP for {self.user.username} - {self.otp}"

    def is_expired(self):
        from django.utils import timezone
        time_diff = timezone.now() - self.created_at
        return time_diff.total_seconds() > 600  # 10 minutes expiry