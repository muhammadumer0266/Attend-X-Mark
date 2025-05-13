from django import forms
from django.contrib.auth.forms import UserCreationForm
from phonenumber_field.formfields import PhoneNumberField
from .models import CustomUser, Teacher, Student
from subjects.models import Department, DegreeLevel, Discipline, Semester, Shift, Section
from django_recaptcha.fields import ReCaptchaField

class UserDetailsForm(forms.ModelForm):
    profile_picture = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'd-none', 'accept': 'image/*'}),
        required=False
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'contact_number', 'profile_picture']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your first name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your last name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your contact number'}),
        }

    # Validation for email uniqueness
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

class ChangePasswordForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password'}),
        required=True,
        label='New Password'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
        required=True,
        label='Confirm Password'
    )

    # Validation for password matching
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned_data

# Form for creating new users
class CustomUserCreationForm(UserCreationForm):
    captcha = ReCaptchaField()
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2', 'captcha')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
        }

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()
    captcha = ReCaptchaField()

class ResetPasswordForm(forms.Form):
    otp = forms.CharField(max_length=6)
    new_password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    captcha = ReCaptchaField()

class UnblockDeviceForm(forms.Form):
    email = forms.EmailField()
    captcha = ReCaptchaField()

class VerifyUnblockOTPForm(forms.Form):
    otp = forms.CharField(max_length=6)
    captcha = ReCaptchaField()

from django.contrib.auth.forms import AuthenticationForm
class CustomAuthenticationForm(AuthenticationForm):
    captcha = ReCaptchaField()

# Form for Teacher additional information
class TeacherAdditionalInfoForm(forms.ModelForm):
    contact_number = PhoneNumberField(
        widget=forms.NumberInput(attrs={'class': 'personal-info-input-text'}),
        label='Contact Number',
        region='PK'
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'personal-info-input-email', 'placeholder': 'Enter your email'})
    )
    profile_picture = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'personal-info-input-file'}),
        required=False
    )

    class Meta:
        model = Teacher
        fields = ['profile_picture', 'email', 'designation', 'department', 'office_room_number', 'specialization', 'contact_number']
        widgets = {
            'designation': forms.Select(attrs={'class': 'personal-info-select'}),
            'department': forms.Select(attrs={'class': 'personal-info-select'}),
            'office_room_number': forms.TextInput(
                attrs={'class': 'personal-info-input-text', 'placeholder': 'Enter office room number'}
            ),
            'specialization': forms.TextInput(
                attrs={'class': 'personal-info-input-text', 'placeholder': 'Enter specialization'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.all()

    # Validation for email uniqueness
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

# Form for Student additional information
class StudentAdditionalInfoForm(forms.ModelForm):
    contact_number = PhoneNumberField(
        widget=forms.NumberInput(attrs={'class': 'personal-info-input-text'}),
        label='Contact Number',
        region='PK'
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'personal-info-input-email', 'placeholder': 'Enter your email'})
    )
    profile_picture = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'personal-info-input-file'}),
        required=False
    )

    class Meta:
        model = Student
        fields = ['profile_picture', 'email', 'contact_number', 'roll_no', 'degree_level', 'discipline', 'semester', 'shift', 'section']
        widgets = {
            'roll_no': forms.TextInput(
                attrs={'class': 'personal-info-input-text', 'placeholder': 'Enter roll number'}
            ),
            'degree_level': forms.Select(attrs={'class': 'personal-info-select'}),
            'section': forms.Select(attrs={'class': 'personal-info-select'}),
            'discipline': forms.Select(attrs={'class': 'personal-info-select'}),
            'semester': forms.Select(attrs={'class': 'personal-info-select'}),
            'shift': forms.Select(attrs={'class': 'personal-info-select'}),
        }

    # Validation for roll number
    def clean_roll_no(self):
        roll_no = self.cleaned_data.get('roll_no')
        if roll_no and Student.objects.exclude(pk=self.instance.pk).filter(roll_no=roll_no).exists():
            raise forms.ValidationError('This Roll No. is already in use.')
        return roll_no

    # Validation for email uniqueness
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['degree_level'].queryset = DegreeLevel.objects.all()
        self.fields['discipline'].queryset = Discipline.objects.all()
        self.fields['semester'].queryset = Semester.objects.all()
        self.fields['shift'].queryset = Shift.objects.all()