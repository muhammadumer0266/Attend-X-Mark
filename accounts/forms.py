from django import forms
from django.contrib.auth.forms import UserCreationForm
from phonenumber_field.formfields import PhoneNumberField
from .models import CustomUser, Teacher, Student
from subjects.models import Department, DegreeLevel, Discipline, Semester


# User Details Form for Profile Settings
class UserDetailsForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['profile_picture', 'email']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'}),
        }

    # Validation for email uniqueness
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

# Form for creating new users
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
        }


# Form for Teacher additional information
class TeacherAdditionalInfoForm(forms.ModelForm):
    contact_number = PhoneNumberField(
        widget=forms.NumberInput(attrs={'class':'form-control'}),
        label='Contact Number',
        region='PK'
    )

    class Meta:
        model = Teacher
        fields = ['designation', 'department', 'office_room_number', 'specialization', 'contact_number']
        widgets = {
            'designation': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'office_room_number': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Enter office room number'}
            ),
            'specialization': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Enter specialization'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.all()


# Form for Student additional information
class StudentAdditionalInfoForm(forms.ModelForm):
    contact_number = PhoneNumberField(
        widget=forms.NumberInput(attrs={'class':'form-control'}),
        label='Contact Number',
        region='PK'
    )

    class Meta:
        model = Student
        fields = ['roll_no', 'degree_level', 'discipline', 'semester', 'contact_number']
        widgets = {
            'roll_no': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Enter roll number'}
            ),
            'degree_level': forms.Select(attrs={'class': 'form-control'}),
            'discipline': forms.Select(attrs={'class': 'form-control'}),
            'semester': forms.Select(attrs={'class': 'form-control'}),
        }

    # Validation for roll number
    def clean_roll_no(self):
        roll_no = self.cleaned_data.get('roll_no')
        if roll_no and Student.objects.exclude(pk=self.instance.pk).filter(roll_no=roll_no).exists():
            raise forms.ValidationError('This Roll No. is already in use.')
        return roll_no

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['degree_level'].queryset = DegreeLevel.objects.all()
        self.fields['discipline'].queryset = Discipline.objects.all()
        self.fields['semester'].queryset = Semester.objects.all()
