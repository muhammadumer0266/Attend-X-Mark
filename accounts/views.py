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
from axes.helpers import get_client_ip_address
from axes.models import AccessAttempt
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from .decorators import teacher_required
from .forms import (
    CustomUserCreationForm,
    UserDetailsForm,
    ChangePasswordForm,
    CustomAuthenticationForm,
    ForgotPasswordForm,
    ResetPasswordForm,
    UnblockDeviceForm,
    VerifyUnblockOTPForm,
    TeacherAdditionalInfoForm,
    StudentAdditionalInfoForm
)
from .models import CustomUser, Teacher, Student, PasswordResetOTP, PersonalInfoOTP
from attendance.models import Leave, AttendanceRecord

def home(request):
    return render(request, 'accounts/home.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Save the user with is_active=False and status='pending'
            user = form.save(commit=False)
            user.is_active = False  # User cannot log in until approved
            user.status = 'pending'  # Ensure status is set to pending
            user.save()
            
            # Send email to user notifying them of the pending approval
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
                send_mail(
                    subject,
                    message,
                    from_email,
                    recipient_list,
                    fail_silently=False,
                )
            except Exception as e:
                messages.warning(request, 'Registration submitted, but failed to send confirmation email.')
            
            messages.success(request, 'Your registration request has been submitted. Please wait for administrator approval.')
            return redirect('login')  # Redirect to login page or a confirmation page
        else:
            for error in form.errors.get('captcha', []):
                messages.error(request, 'Please complete the reCAPTCHA.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('dashboard')
    form_class = CustomAuthenticationForm

    def form_invalid(self, form):
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        CustomUser = get_user_model()

        # Clear any generic non_field_errors to avoid redundancy
        form._errors.pop('__all__', None)

        # Check for reCAPTCHA errors
        if 'captcha' in form.errors:
            messages.error(self.request, 'Please complete the reCAPTCHA.', extra_tags='login_error')
        
        # Check for authentication errors
        if username and password:
            user = authenticate(self.request, username=username, password=password)
            if user is None:
                # Check if the username exists
                if not CustomUser.objects.filter(username=username).exists():
                    messages.error(self.request, 'Invalid username.', extra_tags='login_error')
                else:
                    messages.error(self.request, 'You are entering the wrong password.', extra_tags='login_error')
        
        return super().form_invalid(form)

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Send success email
        user = self.request.user
        subject = 'Successful Login to AttendXMark'
        message = f'Hello {user.username},\n\nYou have successfully logged in to your AttendXMark account.\n\nBest regards,\nThe AttendXMark Team'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]
        
        try:
            send_mail(
                subject,
                message,
                from_email,
                recipient_list,
                fail_silently=False,
            )
        except Exception as e:
            messages.warning(self.request, 'Login successful, but failed to send confirmation email.', extra_tags='login_error')
        
        return response

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
                # Generate a 6-digit OTP
                otp = get_random_string(length=6, allowed_chars='0123456789')
                # Save OTP to the database
                PasswordResetOTP.objects.create(user=user, otp=otp)
                # Send OTP via email
                subject = 'Password Reset OTP - AttendXMark'
                message = f'Hello {user.username},\n\nYour OTP for password reset is: {otp}\n\nPlease use this OTP to reset your password. This OTP is valid for 10 minutes.\n\nBest regards,\nThe AttendXMark Team'
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [user.email]
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
                messages.success(request, 'An OTP has been sent to your email.', extra_tags='login_error')
                return redirect('reset_password')
            except CustomUser.DoesNotExist:
                messages.error(request, 'No user found with this email.', extra_tags='login_error')
        else:
            if 'captcha' in form.errors:
                messages.error(request, 'Please complete the reCAPTCHA.', extra_tags='login_error')
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
                # Check if OTP is within 10 minutes
                time_diff = timezone.now() - otp_record.created_at
                if time_diff.total_seconds() > 600:  # 10 minutes
                    messages.error(request, 'OTP has expired.', extra_tags='login_error')
                    return redirect('reset_password')
                
                if new_password != confirm_password:
                    messages.error(request, 'Passwords do not match.', extra_tags='login_error')
                    return redirect('reset_password')
                
                # Reset the password
                user = otp_record.user
                user.set_password(new_password)
                user.save()
                otp_record.is_used = True
                otp_record.save()
                messages.success(request, 'Password reset successfully. Please login with your new password.', extra_tags='login_error')
                return redirect('login')
            except PasswordResetOTP.DoesNotExist:
                messages.error(request, 'Invalid OTP.', extra_tags='login_error')
                return redirect('reset_password')
        else:
            if 'captcha' in form.errors:
                messages.error(request, 'Please complete the reCAPTCHA.', extra_tags='login_error')
    else:
        form = ResetPasswordForm()
    return render(request, 'accounts/reset_password.html', {'form': form})

def unblock_device_request(request):
    if request.method == 'POST':
        form = UnblockDeviceForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            CustomUser = get_user_model()
            try:
                user = CustomUser.objects.get(email=email)
                # Generate a 6-digit OTP
                otp = get_random_string(length=6, allowed_chars='0123456789')
                # Save OTP to the database
                PasswordResetOTP.objects.create(user=user, otp=otp)
                # Send OTP via email
                subject = 'Device Unblock OTP - AttendXMark'
                message = f'Hello {user.username},\n\nYour OTP to unblock your device is: {otp}\n\nPlease use this OTP to unblock your device. This OTP is valid for 10 minutes.\n\nBest regards,\nThe AttendXMark Team'
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [user.email]
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
                messages.success(request, 'An OTP has been sent to your email.', extra_tags='lockout_error')
                return redirect('unblock_device_verify')
            except CustomUser.DoesNotExist:
                messages.error(request, 'No user found with this email.', extra_tags='lockout_error')
        else:
            if 'captcha' in form.errors:
                messages.error(request, 'Please complete the reCAPTCHA.', extra_tags='lockout_error')
    else:
        form = UnblockDeviceForm()
    return render(request, 'accounts/unblock_device_request.html', {'form': form})

def unblock_device_verify(request):
    if request.method == 'POST':
        form = VerifyUnblockOTPForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data.get('otp')
            try:
                otp_record = PasswordResetOTP.objects.get(otp=otp, is_used=False)
                # Check if OTP is within 10 minutes
                time_diff = timezone.now() - otp_record.created_at
                if time_diff.total_seconds() > 600:  # 10 minutes
                    messages.error(request, 'OTP has expired.', extra_tags='lockout_error')
                    return redirect('unblock_device_verify')
                
                # Reset Axes lockout for the user's device
                ip_address = get_client_ip_address(request)
                AccessAttempt.objects.filter(ip_address=ip_address).delete()
                
                # Mark OTP as used
                otp_record.is_used = True
                otp_record.save()
                messages.success(request, 'Your device has been unblocked. Please try logging in again.', extra_tags='lockout_error')
                return redirect('login')
            except PasswordResetOTP.DoesNotExist:
                messages.error(request, 'Invalid OTP.', extra_tags='lockout_error')
                return redirect('unblock_device_verify')
        else:
            if 'captcha' in form.errors:
                messages.error(request, 'Please complete the reCAPTCHA.', extra_tags='lockout_error')
    else:
        form = VerifyUnblockOTPForm()
    return render(request, 'accounts/unblock_device_verify.html', {'form': form})

@login_required(login_url="/login")
def dashboard(request):
    staff_users = CustomUser.objects.filter(is_staff=True)
    current_date = timezone.now().strftime("%B %d, %Y")

    # Initialize pending leaves count
    if request.user.is_superuser:
        pending_leaves_count = Leave.objects.filter(status='Pending').count()
    elif request.user.is_teacher:
        pending_leaves_count = Leave.objects.filter(
            teacher=request.user, status='Pending'
        ).count()
    elif request.user.is_student:
        pending_leaves_count = Leave.objects.filter(
            user=request.user, status='Pending'
        ).count()
    else:
        pending_leaves_count = 0

    # Calculate attendance records for the teacher this month
    attendance_records_count = 0
    if request.user.is_teacher:
        current_month = timezone.now().month
        current_year = timezone.now().year
        attendance_records_count = AttendanceRecord.objects.filter(
            lecture__teacher=request.user,
            date__year=current_year,
            date__month=current_month
        ).count()

    return render(request, 'accounts/dashboard.html', {
        'staff_users': staff_users,
        'current_date': current_date,
        'pending_leaves_count': pending_leaves_count,
        'attendance_records_count': attendance_records_count  # Add to context
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
            
            # Generate a 6-digit OTP
            otp = get_random_string(length=6, allowed_chars='0123456789')
            
            # Save OTP to the database
            PersonalInfoOTP.objects.create(
                user=request.user,
                email=email,
                otp=otp
            )
            
            # Send OTP via email
            subject = 'Personal Information Update OTP - AttendXMark'
            message = (
                f'Hello {request.user.first_name},\n\n'
                f'Your OTP for updating personal information is: {otp}\n\n'
                'Please use this OTP to verify your email address. This OTP is valid for 10 minutes.\n\n'
                'Best regards,\nThe AttendXMark Team'
            )
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [email]
            
            send_mail(
                subject,
                message,
                from_email,
                recipient_list,
                fail_silently=False,
            )
            
            return JsonResponse({
                'success': True, 
                'message': f'OTP has been sent to {email}'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'message': f'Error sending OTP: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required(login_url="/login")
def personal_info(request):
    user = request.user

    # Initialize forms as None
    teacher_form = None
    student_form = None

    if request.method == 'POST':
        print("POST request received, files:", request.FILES)  # Debug
        
        # Get OTP from form data
        otp_entered = request.POST.get('otp')
        email_entered = request.POST.get('email')
        
        # Verify OTP before processing the form
        if otp_entered and email_entered:
            try:
                otp_record = PersonalInfoOTP.objects.filter(
                    user=user,
                    email=email_entered,
                    otp=otp_entered,
                    is_used=False,
                    is_verified=False
                ).latest('created_at')
                
                if otp_record.is_expired():
                    messages.error(request, 'OTP has expired. Please generate a new one.')
                    # Redirect back to form with error
                    if user.is_teacher:
                        teacher_instance = Teacher.objects.get(id=user.id)
                        teacher_form = TeacherAdditionalInfoForm(instance=teacher_instance)
                    elif user.is_student:
                        student_instance = Student.objects.get(id=user.id)
                        student_form = StudentAdditionalInfoForm(instance=student_instance)
                else:
                    # OTP is valid, mark as verified and proceed with form processing
                    otp_record.is_verified = True
                    otp_record.is_used = True
                    otp_record.save()
                    
                    if user.is_teacher:
                        teacher_instance = Teacher.objects.get(id=user.id)
                        teacher_form = TeacherAdditionalInfoForm(request.POST, request.FILES, instance=teacher_instance)
                        if teacher_form.is_valid():
                            print("Teacher form is valid, saving...")  # Debug
                            teacher = teacher_form.save()
                            # Update the user object's email, contact_number, and profile_picture
                            user.email = teacher_form.cleaned_data['email']
                            user.contact_number = teacher_form.cleaned_data['contact_number']
                            if teacher_form.cleaned_data['profile_picture']:
                                user.profile_picture = teacher_form.cleaned_data['profile_picture']
                            user.save()
                            print("Teacher profile picture after save:", teacher.profile_picture)  # Debug
                            messages.success(request, 'Personal information updated successfully!')
                            return redirect('profile')
                        else:
                            print("Teacher form errors:", teacher_form.errors)
                            messages.error(request, 'Please correct the errors in the form.')
                    elif user.is_student:
                        student_instance = Student.objects.get(id=user.id)
                        student_form = StudentAdditionalInfoForm(request.POST, request.FILES, instance=student_instance)
                        if student_form.is_valid():
                            print("Student form is valid, saving...")  # Debug
                            student = student_form.save()
                            # Update the user object's email, contact_number, and profile_picture
                            user.email = student_form.cleaned_data['email']
                            user.contact_number = student_form.cleaned_data['contact_number']
                            if student_form.cleaned_data['profile_picture']:
                                user.profile_picture = student_form.cleaned_data['profile_picture']
                            user.save()
                            print("Student profile picture after save:", student.profile_picture)  # Debug
                            messages.success(request, 'Personal information updated successfully!')
                            return redirect('profile')
                        else:
                            print("Student form errors:", student_form.errors)
                            messages.error(request, 'Please correct the errors in the form.')
                            
            except PersonalInfoOTP.DoesNotExist:
                messages.error(request, 'Invalid OTP. Please try again.')
                # Redirect back to form with error
                if user.is_teacher:
                    teacher_instance = Teacher.objects.get(id=user.id)
                    teacher_form = TeacherAdditionalInfoForm(instance=teacher_instance)
                elif user.is_student:
                    student_instance = Student.objects.get(id=user.id)
                    student_form = StudentAdditionalInfoForm(instance=student_instance)
        else:
            messages.error(request, 'Please enter OTP to verify your email.')
            # Redirect back to form with error
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
    teacher = student = None

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
def profile_settings(request):
    user = request.user

    if request.method == 'POST':
        # Handle User Details Form
        if 'update_details' in request.POST:
            user_form = UserDetailsForm(request.POST, request.FILES, instance=user)
            if user_form.is_valid():
                user_form.save()
                messages.success(request, 'Your profile has been updated successfully!')
                return redirect('profile')  # Redirect to profile page
            else:
                messages.error(request, 'Error updating your profile. Please check the form.')
        # Handle Password Change Form
        elif 'change_password' in request.POST:
            password_form = ChangePasswordForm(request.POST)
            if password_form.is_valid():
                user.set_password(password_form.cleaned_data['password'])
                user.save()
                messages.success(request, 'Your password has been updated successfully!')
                return redirect('profile')  # Redirect to profile page
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

@teacher_required
def update_teacher_info(request):
    try:
        teacher = Teacher.objects.get(id=request.user.id)
    except Teacher.DoesNotExist:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')

    if request.method == 'POST':
        form = TeacherAdditionalInfoForm(request.POST, instance=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, "Teacher information updated successfully!")
            return redirect('profile')
    else:
        form = TeacherAdditionalInfoForm(instance=teacher)

    return render(request, 'accounts/teacher_info_form.html', {
        'form': form,
        'teacher': teacher
    })

def pending(request):
    return render(request, 'accounts/pending.html')

def privacy_policy(request):
    return render(request, 'accounts/privacy_policy.html')

def offline(request):
    return render(request, 'accounts/offline.html')