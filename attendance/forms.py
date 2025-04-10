from django import forms
from .models import Leave


class LeaveForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = ['subject', 'body', 'leave_date','teacher',]

from django import forms
from accounts.models import CustomUser

class FacialEnrollmentForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['profile_picture']  # For uploading or capturing a photo


from django import forms
from django.forms import formset_factory
from accounts.models import Student
from .models import Attendance

class AttendanceForm(forms.Form):
    student_id = forms.IntegerField(widget=forms.HiddenInput())
    date = forms.DateField(widget=forms.HiddenInput())
    status = forms.ChoiceField(
        choices=[
            ('Present', 'Present'),
            ('Absent', 'Absent'),
            ('Late', 'Late'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
    )

# Create a formset for multiple attendance entries
AttendanceFormSet = formset_factory(AttendanceForm, extra=0)