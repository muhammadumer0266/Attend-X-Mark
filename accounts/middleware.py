# middleware.py
from django.shortcuts import redirect
from django.urls import reverse

class CompleteProfileMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check if contact_number is missing for teacher or student
            if (request.user.is_teacher or request.user.is_student) and not request.user.contact_number:
                # Use the full path of the personal_info URL
                personal_info_path = reverse('personal_info')  # Resolves to /accounts/personal-info/
                if request.path != personal_info_path:  # Avoid redirect loop
                    return redirect('personal_info')
        return self.get_response(request)