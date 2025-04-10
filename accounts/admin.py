from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import mark_safe  # Import mark_safe
from .models import CustomUser,Teacher,Student

class CustomUserAdmin(UserAdmin):
    model = CustomUser

    # Fields to display in the admin user list
    list_display = [
        'email', 'first_name', 'last_name', 
        'profile_picture_display','is_student','is_teacher'
    ]
    search_fields = ['email', 'username']
    ordering = ['email']
    readonly_fields = ['profile_picture_display']  # Read-only profile picture preview

    # Fieldsets for viewing and editing a user
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {
            'fields': (
                'profile_picture', 'profile_picture_display', 
                'first_name', 'last_name'
            )
        }),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser','is_student','is_teacher')}),
        ('Important dates', {'fields': ('last_login',)}),
    )

    # Fieldsets for adding a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2','is_student','is_teacher')}
        ),
    )

    # Function to display profile picture in admin panel
    def profile_picture_display(self, obj):
        # Check if the user has uploaded a profile picture
        if obj.profile_picture:
            # Render the image with safe HTML
            return mark_safe(f'<img loading="lazy" src="{obj.profile_picture.url}" width="30" height="30" style="border-radius: 50%;">')
        return "No Image"  # If no image is uploaded, show this text

    profile_picture_display.short_description = 'Profile Picture'  # Set column header


admin.site.register(CustomUser, CustomUserAdmin)

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'department', 'designation', 'specialization', 'joining_date', 'is_staff')
    search_fields = ('first_name', 'last_name', 'email', 'department__name', 'specialization')
    list_filter = ('designation', 'department', 'is_staff', 'joining_date')
    ordering = ('joining_date',)
    fieldsets = (
        (None, {
            'fields': ('first_name', 'last_name', 'email', 'password')
        }),
        ('Professional Details', {
            'fields': ('department', 'designation', 'specialization', 'office_room_number', 'courses', 'joining_date')
        }),
        ('Permissions', {
            'fields': ('is_superuser', 'groups')
        }),
    )
    # Add filter_horizontal for the 'courses' field
    filter_horizontal = ('courses',)
    


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'roll_no', 'semester', 'discipline', 'degree_level')
    search_fields = ('first_name', 'last_name', 'email', 'roll_no')
    list_filter = ('semester', 'discipline', 'degree_level','is_active')
    ordering = ('roll_no',)

    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email','password', 'profile_picture')
        }),
        ('Academic Information', {
            'fields': ('roll_no', 'semester', 'discipline', 'degree_level','shift',)
        }),
        ('Permissions', {
            'fields': ('is_active','status')
        }),
    )

