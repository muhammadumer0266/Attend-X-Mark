from functools import wraps
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def teacher_required(view_func):
    """Decorator that requires user to be a teacher."""
    @wraps(view_func)
    @login_required(login_url='/login')
    def wrapper(request, *args, **kwargs):
        if not request.user.is_teacher:
            return render(request, 'attendance/access_denied.html', {
                'message': 'You must be a teacher to access this page.'
            })
        return view_func(request, *args, **kwargs)
    return wrapper

def student_required(view_func):
    """Decorator that requires user to be a student."""
    @wraps(view_func)
    @login_required(login_url='/login')
    def wrapper(request, *args, **kwargs):
        if not request.user.is_student:
            return render(request, 'attendance/access_denied.html', {
                'message': 'You must be a student to access this page.'
            })
        return view_func(request, *args, **kwargs)
    return wrapper