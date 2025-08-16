from django.shortcuts import redirect
from django.urls import reverse

class CompleteProfileMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            personal_info_path = reverse('personal_info')  # e.g., /accounts/personal-info/
            otp_generation_path = reverse('generate_personal_info_otp')  # e.g., /generate-personal-info-otp/

            if (
                (request.user.is_teacher or request.user.is_student)
                and not request.user.contact_number
                and request.path not in [personal_info_path, otp_generation_path]
            ):
                return redirect('personal_info')

        return self.get_response(request)