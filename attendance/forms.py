from django import forms
from .models import Leave, Attendance
from django.forms import modelformset_factory

class LeaveForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = ['subject', 'body', 'leave_date', 'lecture']
        widgets = {
            'leave_date': forms.DateInput(attrs={'type': 'date'}),
        }

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
        fields = ['student', 'attendance_status']  # Include 'student' in fields
        widgets = {
            'student': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'attendance_status' in self.initial:
            self.fields['attendance_status'].initial = self.initial['attendance_status']
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
        fields = ['student', 'attendance_status', 'attendance_record']  # Include 'student' and 'attendance_record'
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