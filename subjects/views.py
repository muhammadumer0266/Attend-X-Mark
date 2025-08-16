from django.shortcuts import render
from django.contrib import messages
from subjects.models import Class
from attendance.models import Lecture
from accounts.models import Student
from accounts.decorators import student_required

@student_required
def course_list(request):
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

        # Fetch active lectures for the class
        lectures = Lecture.objects.filter(
            lecture_class=class_instance,
            status='active'
        ).select_related('course', 'teacher').prefetch_related('days').order_by('start_time')

        return render(request, 'subjects/course_list.html', {
            'semester': user_semester,
            'lectures': lectures,
        })
    except Student.DoesNotExist:
        return render(request, 'subjects/course_list.html', {
            'semester': None,
            'lectures': [],
        })