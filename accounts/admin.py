from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import mark_safe
from .models import CustomUser, Teacher, Student
from django import forms
from django.contrib.auth.hashers import make_password
import string
import random

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['email', 'first_name', 'last_name', 'profile_picture_display', 'is_active']
    search_fields = ['email', 'username']
    ordering = ['email']
    readonly_fields = ['profile_picture_display']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('profile_picture', 'profile_picture_display', 'first_name', 'last_name','contact_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_student', 'is_teacher')}),
        ('Important dates', {'fields': ('last_login',)}),
    )
    list_filter = ('is_superuser', 'is_active', 'is_teacher','is_student')
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'is_student', 'is_teacher')}),
    )
    actions = ['set_as_teacher', 'set_as_student']

    def profile_picture_display(self, obj):
        if obj.profile_picture:
            return mark_safe(f'<img loading="lazy" src="{obj.profile_picture.url}" width="30" height="30" style="border-radius: 50%;">')
        return "No Image"
    profile_picture_display.short_description = 'Profile Picture'

    def set_as_teacher(self, request, queryset):
        updated = 0
        for user in queryset:
            user.is_active = True
            user.is_teacher = True
            user.is_student = False
            user.save()  # Save each instance to trigger signals
            updated += 1
        self.message_user(request, f"{updated} user(s) set as teachers.")
    set_as_teacher.short_description = "Set selected users as teachers"

    def set_as_student(self, request, queryset):
        updated = 0
        for user in queryset:
            user.is_active = True
            user.is_student = True
            user.is_teacher = False
            user.save()  # Save each instance to trigger signals
            updated += 1
        self.message_user(request, f"{updated} user(s) set as students.")
    set_as_student.short_description = "Set selected users as students"

class TeacherAdminForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    class Meta:
        model = Teacher
        fields = '__all__'
    def save(self, commit=True):
        if self.cleaned_data.get('password'):
            self.instance.password = make_password(self.cleaned_data['password'])
        return super().save(commit)

class StudentAdminForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    class Meta:
        model = Student
        fields = '__all__'
    def save(self, commit=True):
        if self.cleaned_data.get('password'):
            self.instance.password = make_password(self.cleaned_data['password'])
        return super().save(commit)

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    form = TeacherAdminForm
    list_display = ('first_name', 'last_name', 'email', 'department', 'designation', 'specialization', 'joining_date', 'is_staff')
    search_fields = ('first_name', 'last_name', 'email', 'department__name', 'specialization')
    list_filter = ('designation', 'department', 'is_staff', 'joining_date')
    ordering = ('joining_date',)
    fieldsets = (
        (None, {'fields': ('first_name', 'last_name', 'email', 'password')}),
        ('Professional Details', {'fields': ('department', 'designation', 'specialization', 'office_room_number', 'courses', 'joining_date')}),
        ('Permissions', {'fields': ('is_superuser', 'groups')}),
    )
    filter_horizontal = ('courses',)
    actions = ['reset_password']

    def reset_password(self, request, queryset):
        characters = string.ascii_letters + string.digits + string.punctuation
        for user in queryset:
            new_password = ''.join(random.choice(characters) for _ in range(12))
            user.password = make_password(new_password)
            user.save()
            self.message_user(request, f"Password for {user.email} reset to: {new_password}")
    reset_password.short_description = "Reset password for selected teachers"

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    form = StudentAdminForm
    list_display = ('first_name', 'last_name', 'email', 'department', 'roll_no', 'degree_level', 'discipline', 'semester')
    search_fields = ('first_name', 'last_name', 'email', 'roll_no', 'department__name')
    list_filter = ('semester', 'discipline', 'degree_level', 'department', 'is_active')
    ordering = ('roll_no',)
    fieldsets = (
        ('Personal Information', {'fields': ('first_name', 'last_name', 'email', 'password', 'profile_picture')}),
        ('Academic Information', {'fields': ('department', 'roll_no', 'degree_level', 'discipline', 'semester', 'section', 'shift')}),
        ('Permissions', {'fields': ('is_active',)}),
    )
    actions = ['reset_password']

    def reset_password(self, request, queryset):
        characters = string.ascii_letters + string.digits + string.punctuation
        for user in queryset:
            new_password = ''.join(random.choice(characters) for _ in range(12))
            user.password = make_password(new_password)
            user.save()
            self.message_user(request, f"Password for {user.email} reset to: {new_password}")
    reset_password.short_description = "Reset password for selected students"

admin.site.register(CustomUser, CustomUserAdmin)