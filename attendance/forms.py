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
    ATTENDANCE_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('leave', 'Leave'),
    ]
    attendance_status = forms.ChoiceField(
        choices=ATTENDANCE_CHOICES,
        widget=forms.RadioSelect,
        required=True,
    )

    class Meta:
        model = Attendance
        fields = ['attendance_status']
        widgets = {
            'student': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['attendance_status'].initial = self.instance.attendance_status

class AttendanceEditForm(forms.ModelForm):
    ATTENDANCE_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('leave', 'Leave'),
    ]
    attendance_status = forms.ChoiceField(
        choices=ATTENDANCE_CHOICES,
        widget=forms.Select,
        required=True,
    )

    class Meta:
        model = Attendance
        fields = ['attendance_status']
        widgets = {
            'student': forms.HiddenInput(),
            'attendance_record': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['attendance_status'].initial = self.instance.attendance_status

AttendanceFormSet = modelformset_factory(
    Attendance,
    form=AttendanceForm,
    extra=0
)