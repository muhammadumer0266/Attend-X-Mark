from django.contrib import admin
from .models import Leave, CapturedFace

admin.site.register(Leave)
admin.site.register(CapturedFace)

from django.contrib import admin
from .models import Attendance,Lecture

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('attendance_id', 'student', 'date', 'status')
    list_filter = ('status', 'date')
    search_fields = ('student__username', 'date')
    date_hierarchy = 'date'

    # Optional: Customize the form fields or add inline editing if needed
    fields = ('student', 'date', 'status')
from django.contrib import admin
from .models import Lecture, Day

# Register the Day model (optional, for managing days independently)
@admin.register(Day)
class DayAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Admin configuration for Lecture
from django.contrib import admin
from django import forms
from .models import Lecture

# Custom form for LectureAdmin to use checkboxes for the days field
class LectureAdminForm(forms.ModelForm):
    class Meta:
        model = Lecture
        fields = '__all__'
        widgets = {
            'days': forms.CheckboxSelectMultiple,  # Use checkboxes for ManyToManyField
        }

@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    form = LectureAdminForm  # Use the custom form with the checklist widget
    list_display = ('course', 'teacher', 'lecture_class', 'start_time', 'end_time', 'days_display')
    list_filter = ('course', 'teacher', 'lecture_class', 'days')  # Filter by related days
    search_fields = ('course__code', 'lecture_class__name', 'teacher__username')
    fields = ('teacher', 'course', 'lecture_class', 'start_time', 'end_time', 'days')

    # Custom method to display days in list_display
    def days_display(self, obj):
        return ', '.join(day.name for day in obj.days.all())
    days_display.short_description = 'Days'

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        return formset