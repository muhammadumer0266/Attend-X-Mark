from django import forms
from .models import Leave, Attendance
from accounts.models import Student
from django.forms import modelformset_factory

class LeaveForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = ['subject', 'body', 'leave_date', 'teacher']
        widgets = {
            'leave_date': forms.DateInput(attrs={'type': 'date'}),
        }

class FacialEnrollmentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['profile_picture']

class AttendanceForm(forms.ModelForm):
    student = forms.CharField(widget=forms.HiddenInput())  # Hidden field to store student ID

    class Meta:
        model = Attendance
        fields = ['status']
        widgets = {
            'status': forms.Select(choices=[
                ('Present', 'Present'),
                ('Absent', 'Absent'),
                ('Leave', 'Leave'),
            ])
        }

# Create a formset for marking attendance for multiple students
AttendanceFormSet = modelformset_factory(
    Attendance,
    form=AttendanceForm,
    extra=0  # We'll control the number of forms via the view
)