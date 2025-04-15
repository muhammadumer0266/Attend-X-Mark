from django.contrib import admin
from .models import Leave, CapturedFace, Day, Lecture, Attendance
from django import forms

# Register Leave and CapturedFace
admin.site.register(Leave)
admin.site.register(CapturedFace)

# Register the Day model
@admin.register(Day)
class DayAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Custom form for LectureAdmin
class LectureAdminForm(forms.ModelForm):
    class Meta:
        model = Lecture
        fields = '__all__'
        widgets = {
            'days': forms.CheckboxSelectMultiple,
        }

@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    form = LectureAdminForm
    list_display = ('course', 'teacher', 'lecture_class', 'start_time', 'end_time', 'days_display')
    list_filter = ('course', 'teacher', 'lecture_class', 'days')
    search_fields = ('course__code', 'lecture_class__name', 'teacher__username')
    fields = ('teacher', 'course', 'lecture_class', 'start_time', 'end_time', 'days')

    def days_display(self, obj):
        return ', '.join(day.name for day in obj.days.all())
    days_display.short_description = 'Days'

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'lecture', 'date', 'status', 'is_makeup', 'timestamp')
    list_filter = ('status', 'is_makeup', 'date', 'lecture__course')
    search_fields = ('student__first_name', 'student__last_name', 'lecture__course__code')
    readonly_fields = ('timestamp',)