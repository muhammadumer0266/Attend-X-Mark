from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.urls import reverse_lazy
from datetime import datetime

from .forms import (
    CustomUserCreationForm,
    UserDetailsForm,
    TeacherAdditionalInfoForm,
    StudentAdditionalInfoForm
)
from .models import CustomUser, Teacher, Student
from attendance.models import Leave


def home(request):
    return render(request, 'accounts/home.html')


# Register View
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import UserDetailsForm, TeacherAdditionalInfoForm, StudentAdditionalInfoForm
from .models import Teacher, Student

@login_required(login_url="/login/")
def personal_info(request):
    user = request.user
    teacher_form = student_form = None

    if request.method == 'POST':
        print("POST request received, files:", request.FILES)  # Debug
        form = UserDetailsForm(request.POST, request.FILES, instance=user)

        if user.is_teacher:
            teacher_instance = Teacher.objects.get(id=user.id)
            teacher_form = TeacherAdditionalInfoForm(request.POST, instance=teacher_instance)
        elif user.is_student:
            student_instance = Student.objects.get(id=user.id)
            student_form = StudentAdditionalInfoForm(request.POST, instance=student_instance)

        if form.is_valid() and (not teacher_form or teacher_form.is_valid()) and (not student_form or student_form.is_valid()):
            print("Form is valid, saving...")  # Debug
            form.save()
            if teacher_form:
                teacher_form.save()
            if student_form:
                student_form.save()
            # Refresh the user object from the database
            user.refresh_from_db()
            print("User profile picture after save:", user.profile_picture)  # Debug
            return redirect('profile')
        else:
            print("Form errors:", form.errors)  # Debug
            if teacher_form:
                print("Teacher form errors:", teacher_form.errors)
            if student_form:
                print("Student form errors:", student_form.errors)
    else:
        form = UserDetailsForm(instance=user)
        if user.is_teacher:
            teacher_instance = Teacher.objects.get(id=user.id)
            teacher_form = TeacherAdditionalInfoForm(instance=teacher_instance)
        elif user.is_student:
            student_instance = Student.objects.get(id=user.id)
            student_form = StudentAdditionalInfoForm(instance=student_instance)

    context = {
        'form': form,
        'teacher_form': teacher_form,
        'student_form': student_form,
        'is_teacher': user.is_teacher,
        'is_student': user.is_student
    }
    return render(request, 'accounts/personal_info.html', context)

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('dashboard')

    def get_success_url(self):
        return self.success_url

@login_required(login_url="/accounts/login/")
def dashboard(request):
    staff_users = CustomUser.objects.filter(is_staff=True)
    current_date = datetime.now().strftime("%B %d, %Y")

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

    return render(request, 'accounts/dashboard.html', {
        'staff_users': staff_users,
        'current_date': current_date,
        'pending_leaves_count': pending_leaves_count
    })


@login_required(redirect_field_name='login')
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


@login_required(login_url="/login/")
def profile_settings(request):
    user = request.user

    if request.method == 'POST':
        form = UserDetailsForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile_settings')
        else:
            messages.error(request, 'Error updating your profile. Please check the form.')
    else:
        form = UserDetailsForm(instance=user)

    return render(request, 'accounts/profile_settings.html', {'form': form})


@login_required(login_url="/accounts/login/")
def custom_logout_view(request):
    logout(request)
    return redirect('login')


@login_required
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
