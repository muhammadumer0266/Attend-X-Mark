from django.shortcuts import render, redirect
from django.contrib import messages
from subjects.models import Class
from attendance.models import Lecture
from accounts.models import Student

def course_list(request):
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to view this page.")
        return redirect('login')  # Replace 'login' with your login URL name

    if request.user.is_student:
        try:
            # Get the logged-in student's details
            student = Student.objects.get(id=request.user.id)
            user_semester = student.semester
            user_degree_level = student.degree_level
            user_discipline = student.discipline
            user_shift = student.shift
            user_section = student.section

            # Find the student's class
            class_instance = Class.objects.filter(
                semester=user_semester,
                degree_level=user_degree_level,
                discipline=user_discipline,
                shift=user_shift,
                section=user_section
            ).first()

            if not class_instance:
                messages.warning(request, "No class found for your profile.")
                return render(request, 'subjects/course_list.html', {
                    'semester': user_semester,
                    'lectures': [],
                })

            # Fetch lectures for the class
            lectures = Lecture.objects.filter(lecture_class=class_instance).select_related('course', 'teacher').prefetch_related('days').order_by('start_time')

            return render(request, 'subjects/course_list.html', {
                'semester': user_semester,
                'lectures': lectures,
            })
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
            return render(request, 'subjects/course_list.html', {
                'semester': None,
                'lectures': [],
            })
    else:
        messages.info(request, "This page is only accessible to students.")
        return redirect('profile')  # Replace 'profile' with your profile URL name