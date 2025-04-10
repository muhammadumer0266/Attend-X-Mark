from django.shortcuts import render
from .models import Course

def course_list(request):
    # Get the logged-in user's details
    user_semester = request.user.semester  # User's semester
    user_degree_level = request.user.degree_level  # User's degree level
    user_discipline = request.user.discipline  # User's discipline

    # Fetch courses based on semester, degree level, and discipline
    courses = Course.objects.filter(
        semester=user_semester,
        degree_level=user_degree_level,
        discipline=user_discipline
    )

    return render(request, 'subjects/course_list.html', {
        'semester': user_semester,
        'courses': courses
    })
