from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from attendance.views import authenticate_using_face
from .decorators import teacher_required
from .forms import (
    CustomUserCreationForm,
    UserDetailsForm,
    ChangePasswordForm,
    CustomAuthenticationForm,
    ForgotPasswordForm,
    ResetPasswordForm,
    TeacherAdditionalInfoForm,
    StudentAdditionalInfoForm
)

from .models import CustomUser, Teacher, Student, PasswordResetOTP, PersonalInfoOTP
from attendance.models import Leave, AttendanceRecord,Attendance, Lecture

def get_personal_info_otp_email_template(first_name, last_name, otp):
    """Generate HTML email template for personal information update OTP"""
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Personal Information Update OTP - AttendXMark</title>
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
            .otp-container {{
                background-color: #E0EAF2;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                margin: 25px 0;
                border-left: 4px solid #457b9d;
            }}
            .otp-code {{
                font-size: 32px;
                font-weight: 700;
                color: #1d3557;
                letter-spacing: 5px;
                margin-bottom: 15px;
            }}
            .copy-button {{
                display: inline-block;
                background: linear-gradient(135deg, #457b9d 0%, #1d3557 100%);
                color: white;
                padding: 12px 25px;
                border-radius: 50px;
                font-size: 14px;
                font-weight: 500;
                text-decoration: none;
                cursor: pointer;
                box-shadow: 0 4px 15px rgba(69, 123, 157, 0.3);
                transition: all 0.3s ease;
            }}
            .copy-button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(69, 123, 157, 0.4);
            }}
            .copy-button.copied {{
                background: linear-gradient(135deg, #28a745 0%, #218838 100%);
            }}
            .message-text p {{
                margin-bottom: 15px;
                color: #1d3557;
                font-size: 16px;
                line-height: 1.7;
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
                .otp-code {{
                    font-size: 28px;
                    letter-spacing: 3px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h1>🔒 Personal Information Update</h1>
                <p style="color:white;">Verify Your Request with OTP</p>
            </div>
            <div class="content">
                <div class="welcome-message">
                    <h2>Hello <span class="user-name">{first_name} {last_name}</span>!</h2>
                </div>
                <div class="divider"></div>
                <div class="message-text">
                    <p>You have requested to update your personal information with AttendXMark.</p>
                    <p>Please use the OTP below to verify your request. This OTP is valid for 10 minutes.</p>
                </div>
                <div class="otp-container">
                    <div class="otp-code">{otp}</div>
                </div>
                <div class="message-text">
                    <p><strong>Next Steps:</strong></p>
                    <p>• Enter the OTP in the verification field</p>
                    <p>• Complete your information update</p>
                    <p>• Contact support if you need assistance</p>
                </div>
            </div>
            <div class="footer">
                <p>Thank you for choosing <span class="company-name">AttendXMark</span></p>
                <p>Making attendance management smarter, one click at a time</p>
            </div>
        </div>
        <script>
            function copyOTP(otp, button) {{
                navigator.clipboard.writeText(otp).then(() => {{
                    button.textContent = 'Copied!';
                    button.classList.add('copied');
                    setTimeout(() => {{
                        button.textContent = 'Copy OTP';
                        button.classList.remove('copied');
                    }}, 2000);
                }}).catch(err => {{
                    console.error('Failed to copy OTP: ', err);
                    button.textContent = 'Error';
                    setTimeout(() => {{
                        button.textContent = 'Copy OTP';
                    }}, 2000);
                }});
            }}
        </script>
    </body>
    </html>
    """
    return html_template

def get_forgot_password_otp_email_template(first_name, last_name, otp):
    """Generate HTML email template for forgot password OTP"""
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Password Reset OTP - AttendXMark</title>
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
            .otp-container {{
                background-color: #E0EAF2;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                margin: 25px 0;
                border-left: 4px solid #457b9d;
            }}
            .otp-code {{
                font-size: 32px;
                font-weight: 700;
                color: #1d3557;
                letter-spacing: 5px;
                margin-bottom: 15px;
            }}
            .copy-button {{
                display: inline-block;
                background: linear-gradient(135deg, #457b9d 0%, #1d3557 100%);
                color: white;
                padding: 12px 25px;
                border-radius: 50px;
                font-size: 14px;
                font-weight: 500;
                text-decoration: none;
                cursor: pointer;
                box-shadow: 0 4px 15px rgba(69, 123, 157, 0.3);
                transition: all 0.3s ease;
            }}
            .copy-button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(69, 123, 157, 0.4);
            }}
            .copy-button.copied {{
                background: linear-gradient(135deg, #28a745 0%, #218838 100%);
            }}
            .message-text p {{
                margin-bottom: 15px;
                color: #1d3557;
                font-size: 16px;
                line-height: 1.7;
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
                .otp-code {{
                    font-size: 28px;
                    letter-spacing: 3px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h1>🔑 Password Reset Request</h1>
                <p style="color:white;">Secure Your Account with OTP</p>
            </div>
            <div class="content">
                <div class="welcome-message">
                    <h2>Hello <span class="user-name">{first_name} {last_name}</span>!</h2>
                </div>
                <div class="divider"></div>
                <div class="message-text">
                    <p>You have requested to reset your password for your AttendXMark account.</p>
                    <p>Please use the OTP below to verify your request. This OTP is valid for 10 minutes.</p>
                </div>
                <div class="otp-container">
                    <div class="otp-code">{otp}</div>
                </div>
                <div class="message-text">
                    <p><strong>Next Steps:</strong></p>
                    <p>• Enter the OTP in the password reset form</p>
                    <p>• Set your new password</p>
                    <p>• Contact support if you need assistance</p>
                </div>
            </div>
            <div class="footer">
                <p>Thank you for choosing <span class="company-name">AttendXMark</span></p>
                <p>Making attendance management smarter, one click at a time</p>
            </div>
        </div>
        <script>
            function copyOTP(otp, button) {{
                navigator.clipboard.writeText(otp).then(() => {{
                    button.textContent = 'Copied!';
                    button.classList.add('copied');
                    setTimeout(() => {{
                        button.textContent = 'Copy OTP';
                        button.classList.remove('copied');
                    }}, 2000);
                }}).catch(err => {{
                    console.error('Failed to copy OTP: ', err);
                    button.textContent = 'Error';
                    setTimeout(() => {{
                        button.textContent = 'Copy OTP';
                    }}, 2000);
                }});
            }}
        </script>
    </body>
    </html>
    """
    return html_template

def home(request):
    return render(request, 'accounts/home.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            
            subject = 'Registration Request Received - AttendXMark'
            message = (
                f'Hello {user.first_name} {user.last_name},\n\n'
                'Your registration request has been successfully submitted to AttendXMark.\n'
                'Please wait for administrator approval. We will notify you via email once your account is approved.\n\n'
                'Best regards,\nThe AttendXMark Team'
            )
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [user.email]
            
            try:
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
            except Exception as e:
                messages.warning(request, 'Registration submitted, but failed to send confirmation email.')
            
            messages.success(request, 'Your registration request has been submitted. Please wait for administrator approval.')
            return redirect('login')
        else:
            for error in form.errors.get('captcha', []):
                messages.error(request, 'Please complete the reCAPTCHA.', extra_tags='login_error')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('dashboard')
    form_class = CustomAuthenticationForm

    def form_invalid(self, form):
        email = form.data.get('username')
        password = form.data.get('password')
        CustomUser = get_user_model()
        if 'captcha' in form.errors:
            messages.error(self.request,'Please complete the reCAPTCHA.',extra_tags='danger')
            return self.render_to_response(self.get_context_data(form=form))
        if email and password:
            user = CustomUser.objects.filter(email=email).first()
            if not user:
                messages.error(self.request,'Invalid email address.',extra_tags='danger')
            else:
                if not user.is_active:
                    messages.success(self.request,'Your request is under process. We will notify you once it is approved.',extra_tags='success')
                else:
                    if not authenticate(self.request, username=email, password=password):
                        messages.error(self.request,'Invalid password.',extra_tags='danger')

        return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        return super().form_valid(form)

    def get_success_url(self):
        return self.success_url
    
def forgot_password(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            CustomUser = get_user_model()
            try:
                user = CustomUser.objects.get(email=email)
                otp = get_random_string(length=6, allowed_chars='0123456789')
                PasswordResetOTP.objects.create(user=user, otp=otp)
                subject = 'Password Reset OTP - AttendXMark'
                message = get_forgot_password_otp_email_template(user.first_name, user.last_name, otp)
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [user.email]
                send_mail(subject, '', from_email, recipient_list, html_message=message, fail_silently=False)
                messages.success(request, 'An OTP has been sent to your email.', extra_tags='forgot_password_success')  # Changed tag
                return redirect('reset_password')
            except CustomUser.DoesNotExist:
                messages.error(request, 'No user found with this email.', extra_tags='forgot_password_error')  # Changed tag
        else:
            if 'captcha' in form.errors:
                messages.error(request, 'Please complete the reCAPTCHA.', extra_tags='forgot_password_error')  # Changed tag
    else:
        form = ForgotPasswordForm()
    return render(request, 'accounts/forgot_password.html', {'form': form})

def reset_password(request):
    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data.get('otp')
            new_password = form.cleaned_data.get('new_password')
            confirm_password = form.cleaned_data.get('confirm_password')
            
            try:
                otp_record = PasswordResetOTP.objects.get(otp=otp, is_used=False)
                time_diff = timezone.now() - otp_record.created_at
                if time_diff.total_seconds() > 600:
                    messages.error(request, 'OTP has expired.', extra_tags='danger')  # Changed tag
                    return redirect('reset_password')
                
                if new_password != confirm_password:
                    messages.error(request, 'Passwords do not match.', extra_tags='danger')  # Changed tag
                    return redirect('reset_password')
                
                user = otp_record.user
                user.set_password(new_password)
                user.save()
                otp_record.is_used = True
                otp_record.save()
                messages.success(request, 'Password reset successfully. Please login with your new password.', extra_tags='success')  # Changed tag
                return redirect('login')
            except PasswordResetOTP.DoesNotExist:
                messages.error(request, 'Invalid OTP.', extra_tags='danger')  # Changed tag
        else:
            if 'captcha' in form.errors:
                messages.error(request, 'Please complete the reCAPTCHA.', extra_tags='danger')  # Changed tag
    else:
        form = ResetPasswordForm()
    return render(request, 'accounts/reset_password.html', {'form': form})


@login_required(login_url="/login")
def dashboard(request):
    current_date = timezone.now().strftime("%B %d, %Y")

    if request.user.is_superuser:
        pending_leaves_count = Leave.objects.filter(status='Pending').count()
    elif request.user.is_teacher:
        pending_leaves_count = Leave.objects.filter(teacher=request.user, status='Pending').count()
    elif request.user.is_student:
        pending_leaves_count = Leave.objects.filter(user=request.user, status='Pending').count()
    else:
        pending_leaves_count = 0

    attendance_records_count = 0
    overall_attendance_percentage = 0
    if request.user.is_teacher:
        current_month = timezone.now().month
        current_year = timezone.now().year
        attendance_records_count = AttendanceRecord.objects.filter(
            lecture__teacher=request.user,
            date__year=current_year,
            date__month=current_month
        ).count()
    elif request.user.is_student:
        student = Student.objects.get(id=request.user.id)
        current_semester = student.semester
        # Get all lectures for the student's class in the current semester
        lectures = Lecture.objects.filter(
            lecture_class__semester=current_semester,
            lecture_class__degree_level=student.degree_level,
            lecture_class__discipline=student.discipline,
            lecture_class__section=student.section,
            lecture_class__shift=student.shift,
            status='active'
        )
        total_classes = Attendance.objects.filter(
            student=student,
            attendance_record__lecture__in=lectures
        ).count()
        present_classes = Attendance.objects.filter(
            student=student,
            attendance_record__lecture__in=lectures,
            attendance_status='present'
        ).count()
        overall_attendance_percentage = (present_classes / total_classes * 100) if total_classes > 0 else 0

    # Get current user's department
    user_department = None
    if request.user.is_teacher:
        user_department = request.user.teacher.department
    elif request.user.is_student:
        user_department = request.user.student.department

    # Filter staff users who are teachers and match the department
    staff_users = Teacher.objects.filter(
        is_teacher=True,
        department=user_department
    ) if user_department else []

    return render(request, 'accounts/dashboard.html', {
        'staff_users': staff_users,
        'current_date': current_date,
        'pending_leaves_count': pending_leaves_count,
        'attendance_records_count': attendance_records_count,
        'overall_attendance_percentage': round(overall_attendance_percentage, 2)
    })

@login_required(login_url="/login")
@csrf_exempt
def generate_personal_info_otp(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            
            if not email:
                return JsonResponse({'success': False, 'message': 'Email is required'})
            
            otp = get_random_string(length=6, allowed_chars='0123456789')
            PersonalInfoOTP.objects.create(user=request.user, email=email, otp=otp)
            
            subject = 'Personal Information Update OTP - AttendXMark'
            message = get_personal_info_otp_email_template(request.user.first_name, request.user.last_name, otp)
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [email]
            
            send_mail(subject, '', from_email, recipient_list, html_message=message, fail_silently=False)
            
            return JsonResponse({'success': True, 'message': f'OTP has been sent to {email}'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error sending OTP: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required(login_url="/login")
def personal_info(request):
    user = request.user
    teacher_form = None
    student_form = None

    if request.method == 'POST':
        otp_entered = request.POST.get('otp')
        email_entered = request.POST.get('email')
        
        if otp_entered and email_entered:
            try:
                otp_record = PersonalInfoOTP.objects.filter(
                    user=user, email=email_entered, otp=otp_entered, is_used=False, is_verified=False
                ).latest('created_at')
                
                if otp_record.is_expired():
                    messages.error(request, 'OTP has expired. Please generate a new one.')
                    if user.is_teacher:
                        teacher_instance = Teacher.objects.get(id=user.id)
                        teacher_form = TeacherAdditionalInfoForm(instance=teacher_instance)
                    elif user.is_student:
                        student_instance = Student.objects.get(id=user.id)
                        student_form = StudentAdditionalInfoForm(instance=student_instance)
                else:
                    otp_record.is_verified = True
                    otp_record.is_used = True
                    otp_record.save()
                    
                    if user.is_teacher:
                        teacher_instance = Teacher.objects.get(id=user.id)
                        teacher_form = TeacherAdditionalInfoForm(request.POST, request.FILES, instance=teacher_instance)
                        if teacher_form.is_valid():
                            teacher = teacher_form.save()
                            user.email = teacher_form.cleaned_data['email']
                            user.contact_number = teacher_form.cleaned_data['contact_number']
                            if teacher_form.cleaned_data['profile_picture']:
                                user.profile_picture = teacher_form.cleaned_data['profile_picture']
                            user.save()
                            messages.success(request, 'Personal information updated successfully!')
                            return redirect('profile')
                        else:
                            messages.error(request, 'Please correct the errors in the form.')
                    elif user.is_student:
                        student_instance = Student.objects.get(id=user.id)
                        student_form = StudentAdditionalInfoForm(request.POST, request.FILES, instance=student_instance)
                        if student_form.is_valid():
                            student = student_form.save()
                            user.email = student_form.cleaned_data['email']
                            user.contact_number = student_form.cleaned_data['contact_number']
                            if student_form.cleaned_data['profile_picture']:
                                user.profile_picture = student_form.cleaned_data['profile_picture']
                            user.save()
                            messages.success(request, 'Personal information updated successfully!')
                            return redirect('profile')
                        else:
                            messages.error(request, 'Please correct the errors in the form.')
                            
            except PersonalInfoOTP.DoesNotExist:
                messages.error(request, 'Invalid OTP. Please try again.')
                if user.is_teacher:
                    teacher_instance = Teacher.objects.get(id=user.id)
                    teacher_form = TeacherAdditionalInfoForm(instance=teacher_instance)
                elif user.is_student:
                    student_instance = Student.objects.get(id=user.id)
                    student_form = StudentAdditionalInfoForm(instance=student_instance)
        else:
            messages.error(request, 'Please enter OTP to verify your email.')
            if user.is_teacher:
                teacher_instance = Teacher.objects.get(id=user.id)
                teacher_form = TeacherAdditionalInfoForm(request.POST, request.FILES, instance=teacher_instance)
            elif user.is_student:
                student_instance = Student.objects.get(id=user.id)
                student_form = StudentAdditionalInfoForm(request.POST, request.FILES, instance=student_instance)
    else:
        if user.is_teacher:
            teacher_instance = Teacher.objects.get(id=user.id)
            teacher_form = TeacherAdditionalInfoForm(instance=teacher_instance)
        elif user.is_student:
            student_instance = Student.objects.get(id=user.id)
            student_form = StudentAdditionalInfoForm(instance=student_instance)

    context = {
        'teacher_form': teacher_form,
        'student_form': student_form,
        'is_teacher': user.is_teacher,
        'is_student': user.is_student
    }
    return render(request, 'accounts/personal_info.html', context)

@login_required(login_url="/login")
def profile(request):
    user = request.user
    teacher = None
    student = None

    if user.is_teacher:
        teacher = Teacher.objects.filter(id=user.id).first()
    elif user.is_student:
        student = Student.objects.filter(id=user.id).first()

    return render(request, 'accounts/profile.html', {
        'user': user,
        'teacher': teacher,
        'student': student
    })

@login_required(login_url="/login")
@authenticate_using_face
def profile_settings(request):
    user = request.user
    messages.get_messages(request).used = True  # Clear previous messages
    if request.method == 'POST':
        if 'update_details' in request.POST:
            user_form = UserDetailsForm(request.POST, request.FILES, instance=user)
            if user_form.is_valid():
                user_form.save()
                messages.success(request, 'Your profile has been updated successfully!')
                return redirect('profile')
            else:
                messages.error(request, 'Error updating your profile. Please check the form.')
        elif 'change_password' in request.POST:
            password_form = ChangePasswordForm(request.POST)
            if password_form.is_valid():
                user.set_password(password_form.cleaned_data['password'])
                user.save()
                messages.success(request, 'Your password has been updated successfully!')
                return redirect('profile')
            else:
                messages.error(request, 'Error updating your password. Please check the form.')
    else:
        user_form = UserDetailsForm(instance=user)
        password_form = ChangePasswordForm()

    return render(request, 'accounts/profile_settings.html', {'user_form': user_form, 'password_form': password_form})

@login_required(login_url="/login")
def custom_logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def account_pending_view(request):
    return render(request, 'accounts/account_pending.html')

def privacy_policy(request):
    return render(request, 'accounts/privacy_policy.html')

def offline(request):
    return render(request, 'accounts/offline.html')

def lockout(request):
    return render(request, 'accounts/lockout.html')