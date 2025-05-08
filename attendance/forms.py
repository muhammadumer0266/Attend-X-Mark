from django import forms
from .models import Leave
from accounts.models import Student
from django.forms import modelformset_factory

class LeaveForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = ['subject', 'body', 'leave_date', 'teacher']
        widgets = {
            'leave_date': forms.DateInput(attrs={'type': 'date'}),
        }


from django import forms
from .models import Attendance
from accounts.models import Student

class AttendanceForm(forms.ModelForm):
    # Define choices explicitly to avoid blank option
    ATTENDANCE_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('leave', 'Leave'),
        # Add other statuses if needed, e.g., ('late', 'Late')
    ]

    # Use ChoiceField with RadioSelect instead of model field directly
    attendance_status = forms.ChoiceField(
        choices=ATTENDANCE_CHOICES,
        widget=forms.RadioSelect,
        required=True,  # Ensure no blank option
    )

    class Meta:
        model = Attendance
        fields = ['student', 'attendance_status']
        widgets = {
            'student': forms.HiddenInput(),
        }

AttendanceFormSet = forms.modelformset_factory(
    Attendance,
    form=AttendanceForm,
    extra=0
)