from django import forms
from django.contrib.auth.forms import UserCreationForm
from phonenumber_field.formfields import PhoneNumberField
from .models import CustomUser, Teacher, Student
from subjects.models import Department, DegreeLevel, Discipline, Semester


from django import forms
from accounts.models import CustomUser

class UserDetailsForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password'}),
        required=False,
        label='New Password'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
        required=False,
        label='Confirm Password'
    )

    class Meta:
        model = CustomUser
        fields = ['profile_picture', 'first_name', 'last_name', 'email', 'contact_number', 'password']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your first name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your last name'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your contact number'}),
        }

    # Validation for email uniqueness
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    # Validation for password matching
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Passwords do not match.')
        elif password and not confirm_password:
            self.add_error('confirm_password', 'Please confirm your password.')
        elif confirm_password and not password:
            self.add_error('password', 'Please enter a password.')
        return cleaned_data

    # Override save to hash the password
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)  # Hash the password
        if commit:
            user.save()
        return user
from django_recaptcha.fields import ReCaptchaField

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

from django.contrib.auth.forms import AuthenticationForm
class CustomAuthenticationForm(AuthenticationForm):
    captcha = ReCaptchaField()

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
        fields = ['roll_no', 'degree_level', 'discipline', 'semester', 'contact_number','section']
        widgets = {
            'roll_no': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Enter roll number'}
            ),
            'degree_level': forms.Select(attrs={'class': 'form-control'}),
            'section': forms.Select(attrs={'class': 'form-control'}),
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
