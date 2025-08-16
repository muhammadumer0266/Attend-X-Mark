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

# Initialize MTCNN and InceptionResnetV1 for face detection and embedding
mtcnn = MTCNN(image_size=160, margin=0, min_face_size=20)
resnet = InceptionResnetV1(pretrained='vggface2').eval()


# ------------------ Email Template Function ------------------
def get_activation_email_template(first_name, last_name):
    """Generate HTML email template for account activation"""
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Account Activated - AttendXMark</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Poppins', Arial, sans-serif;
                background-color: #E0EAF2;
                color: #1d3557;
                line-height: 1.6;
            }}
            
            .email-container {{
                max-width: 600px;
                margin: 40px auto;
                background-color: #ffffff;
                border-radius: 12px;
                box-shadow: 0 8px 25px rgba(29, 53, 87, 0.1);
                overflow: hidden;
            }}
            
            .header {{
                background: linear-gradient(135deg, #457b9d 0%, #1d3557 100%);
                padding: 40px 30px;
                text-align: center;
                color: white;
            }}
            
            .header h1 {{
                font-size: 28px;
                font-weight: 600;
                margin-bottom: 10px;
                letter-spacing: -0.5px;
            }}
            
            .header p {{
                font-size: 16px;
                font-weight: 300;
                opacity: 0.9;
            }}
            
            .content {{
                padding: 40px 30px;
                background-color: #ffffff;
            }}
            
            .welcome-message {{
                text-align: center;
                margin-bottom: 30px;
            }}
            
            .welcome-message h2 {{
                color: #1d3557;
                font-size: 24px;
                font-weight: 600;
                margin-bottom: 10px;
            }}
            
            .user-name {{
                color: #457b9d;
                font-weight: 500;
            }}
            
            .message-text {{
                background-color: #E0EAF2;
                padding: 25px;
                border-radius: 8px;
                margin: 25px 0;
                border-left: 4px solid #457b9d;
            }}
            
            .message-text p {{
                margin-bottom: 15px;
                color: #1d3557;
                font-size: 16px;
                line-height: 1.7;
            }}
            
            .message-text p:last-child {{
                margin-bottom: 0;
            }}
            
            .cta-section {{
                text-align: center;
                margin: 35px 0;
            }}
            
            .cta-button {{
                display: inline-block;
                background: linear-gradient(135deg, #457b9d 0%, #1d3557 100%);
                color: white;
                padding: 15px 35px;
                text-decoration: none;
                border-radius: 50px;
                font-weight: 500;
                font-size: 16px;
                box-shadow: 0 4px 15px rgba(69, 123, 157, 0.3);
                transition: all 0.3s ease;
            }}
            
            .cta-button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(69, 123, 157, 0.4);
            }}
            
            .footer {{
                background-color: #f8f9fa;
                padding: 25px 30px;
                text-align: center;
                border-top: 1px solid #E0EAF2;
            }}
            
            .footer p {{
                color: #457b9d;
                font-size: 14px;
                margin-bottom: 5px;
            }}
            
            .footer .company-name {{
                font-weight: 600;
                color: #1d3557;
            }}
            
            .divider {{
                height: 3px;
                background: linear-gradient(90deg, #457b9d 0%, #1d3557 100%);
                margin: 20px 0;
                border-radius: 2px;
            }}
            
            @media only screen and (max-width: 600px) {{
                .email-container {{
                    margin: 20px;
                    border-radius: 8px;
                }}
                
                .header {{
                    padding: 30px 20px;
                }}
                
                .content {{
                    padding: 30px 20px;
                }}
                
                .header h1 {{
                    font-size: 24px;
                }}
                
                .welcome-message h2 {{
                    font-size: 20px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h1>🎉 Account Activated!</h1>
                <p style="color:white;">Welcome to the AttendXMark Family</p>
            </div>
            
            <div class="content">
                <div class="welcome-message">
                    <h2>Hello <span class="user-name">{first_name} {last_name}</span>!</h2>
                </div>
                
                <div class="divider"></div>
                
                <div class="message-text">
                    <p><strong>🎊 Congratulations!</strong> Your account with AttendXMark has been successfully activated by our administrator.</p>
                    
                    <p>You now have full access to all the features and can start managing attendance with ease. Your journey with modern attendance management begins now!</p>
                </div>
                
                <div class="cta-section">
                    <a href="#" class="cta-button" style="color:white;">🚀 Login to Your Account</a>
                </div>
                
                <div class="message-text">
                    <p><strong>Next Steps:</strong></p>
                    <p>• Use your email address and password to log in</p>
                    <p>• Complete your profile setup</p>
                    <p>• Explore the dashboard and available features</p>
                    <p>• Contact support if you need any assistance</p>
                </div>
            </div>
            
            <div class="footer">
                <p>Thank you for choosing <span class="company-name">AttendXMark</span></p>
                <p>A Smart attendance solution.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_template


# ------------------ Custom User Manager ------------------
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


# ------------------ Custom User Model ------------------
class CustomUser(AbstractBaseUser, PermissionsMixin):
    profile_picture = models.ImageField(upload_to='profile_pics/', default='profile_pics/defpic.png')
    username = models.CharField(max_length=150, unique=True, blank=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    contact_number = PhoneNumberField(_("Contact Number"), region="PK", blank=True, null=True)
    face_encoding = models.BinaryField(blank=True, null=True)

    is_teacher = models.BooleanField(default=False)
    is_student = models.BooleanField(default=False)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email


# ------------------ Signals ------------------

# Set username from email
@receiver(pre_save, sender=CustomUser)
def set_username_from_email(sender, instance, **kwargs):
    if instance.email and not instance.username:
        instance.username = instance.email.split('@')[0]


# Store old is_active value before save
@receiver(pre_save, sender=CustomUser)
def store_old_is_active(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_is_active = old_instance.is_active
        except sender.DoesNotExist:
            instance._old_is_active = instance.is_active
    else:
        instance._old_is_active = instance.is_active


# Generate face encoding after save
@receiver(post_save, sender=CustomUser)
def generate_face_encoding(sender, instance, created, **kwargs):
    if instance.profile_picture and instance.profile_picture != 'profile_pics/defpic.png':
        try:
            img = Image.open(instance.profile_picture.path).convert('RGB')
            boxes, _ = mtcnn.detect(img)
            num_faces = len(boxes) if boxes is not None else 0

            post_save.disconnect(generate_face_encoding, sender=CustomUser)
            try:
                if num_faces == 1:
                    img_cropped = mtcnn(img, return_prob=False)
                    if img_cropped is not None:
                        img_cropped = img_cropped.unsqueeze(0)
                        with torch.no_grad():
                            embedding = resnet(img_cropped).detach().cpu().numpy()
                        instance.face_encoding = pickle.dumps(embedding)
                    else:
                        instance.face_encoding = None
                        instance.profile_picture = 'profile_pics/defpic.png'
                else:
                    instance.face_encoding = None
                    instance.profile_picture = 'profile_pics/defpic.png'

                instance.save(update_fields=['face_encoding', 'profile_picture'])
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


# Create/update Teacher or Student record
@receiver(post_save, sender=CustomUser)
def create_teacher_or_student(sender, instance, created, **kwargs):
    if instance.is_teacher and instance.is_student:
        raise ValueError("A user cannot be both a teacher and a student.")

    post_save.disconnect(create_teacher_or_student, sender=CustomUser)
    post_save.disconnect(generate_face_encoding, sender=CustomUser)
    try:
        if instance.is_teacher:
            teacher, _ = Teacher.objects.update_or_create(
                id=instance.id,
                defaults={
                    'profile_picture': instance.profile_picture,
                    'username': instance.username,
                    'first_name': instance.first_name,
                    'last_name': instance.last_name,
                    'email': instance.email,
                    'password': instance.password,
                    'face_encoding': instance.face_encoding,
                    'is_teacher': True,
                    'is_student': False,
                    'is_active': instance.is_active,
                    'is_staff': True,
                }
            )
            instance.password = teacher.password
            instance.save(update_fields=['password'])
        elif instance.is_student:
            student, _ = Student.objects.update_or_create(
                id=instance.id,
                defaults={
                    'profile_picture': instance.profile_picture,
                    'username': instance.username,
                    'first_name': instance.first_name,
                    'last_name': instance.last_name,
                    'email': instance.email,
                    'password': instance.password,
                    'face_encoding': instance.face_encoding,
                    'is_teacher': False,
                    'is_student': True,
                    'is_active': instance.is_active,
                    'is_staff': False,
                }
            )
            instance.password = student.password
            instance.save(update_fields=['password'])
    finally:
        post_save.connect(create_teacher_or_student, sender=CustomUser)
        post_save.connect(generate_face_encoding, sender=CustomUser)


# Notify user on approval - Now with beautiful HTML email template
@receiver(post_save, sender=CustomUser)
def notify_user_on_approval(sender, instance, created, **kwargs):
    if created:
        return

    print(f"[DEBUG] Post-save for {instance.email}, old_is_active={getattr(instance, '_old_is_active', None)}, new_is_active={instance.is_active}")

    if getattr(instance, '_old_is_active', False) is False and instance.is_active:
        print(f"[DEBUG] Sending activation email to {instance.email}")
        
        from django.core.mail import send_mail
        
        try:
            # Generate the HTML email template
            html_message = get_activation_email_template(instance.first_name, instance.last_name)
            
            # Plain text version for email clients that don't support HTML
            plain_text_message = (
                f'Hello {instance.first_name} {instance.last_name},\n\n'
                '🎊 Congratulations! Your account with AttendXMark has been successfully activated by our administrator.\n\n'
                'You now have full access to all the features and can start managing attendance with ease. '
                'Your journey with modern attendance management begins now!\n\n'
                'Next Steps:\n'
                '• Use your email address and password to log in\n'
                '• Complete your profile setup\n'
                '• Explore the dashboard and available features\n'
                '• Contact support if you need any assistance\n\n'
                'Thank you for choosing AttendXMark\n'
                'A Smart attendance solution.\n\n'
                'Best regards,\n'
                'The AttendXMark Team'
            )
            
            # Send HTML email
            from django.core.mail import EmailMultiAlternatives
            
            email = EmailMultiAlternatives(
                subject='🎉 Account Activated - AttendXMark',
                body=plain_text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[instance.email]
            )   
            email.attach_alternative(html_message, "text/html")
            email.send()
            
            print(f"[DEBUG] Beautiful activation email sent successfully to {instance.email}")
            
        except Exception as e:
            print(f"Error sending activation email to {instance.email}: {str(e)}")


# ------------------ Teacher Model ------------------
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
    designation = models.CharField(max_length=20, choices=DESIGNATION_CHOICES, default=None, blank=True, null=True)
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


# ------------------ Student Model ------------------
class Student(CustomUser):
    roll_no = models.CharField(max_length=20, unique=True, null=True, blank=True)
    degree_level = models.ForeignKey(DegreeLevel, on_delete=models.SET_NULL, null=True, blank=True)
    discipline = models.ForeignKey(Discipline, on_delete=models.SET_NULL, null=True, blank=True)
    semester = models.ForeignKey(Semester, on_delete=models.SET_NULL, null=True, blank=True)
    shift = models.ForeignKey('subjects.Shift', on_delete=models.SET_NULL, null=True, blank=True)
    section = models.ForeignKey('subjects.Section', on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    class Meta:
        verbose_name = "Student"
        verbose_name_plural = "Students"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.roll_no or self.email})"


# ------------------ OTP Models ------------------
from django.contrib.auth import get_user_model
CustomUser = get_user_model()


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"OTP for {self.user.username} - {self.otp}"


class PersonalInfoOTP(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Personal Info OTP for {self.user.username} - {self.otp}"

    def is_expired(self):
        from django.utils import timezone
        return (timezone.now() - self.created_at).total_seconds() > 600