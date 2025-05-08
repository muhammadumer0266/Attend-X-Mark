from django.contrib import admin
from .models import Leave, Day, Lecture
from django import forms

# Register Leave and CapturedFace
admin.site.register(Leave)

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


from django.contrib import admin
from .models import AttendanceRecord, Attendance


class AttendanceInline(admin.TabularInline):
    model = Attendance
    extra = 0
    autocomplete_fields = ['student']
    fields = ['student', 'attendance_status']
    readonly_fields = []
    can_delete = True


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['lecture', 'date','is_makeup_class']
    list_filter = ['date', 'lecture__course', 'lecture__lecture_class','is_makeup_class']
    search_fields = ['lecture__course__code', 'lecture__lecture_class__name']
    date_hierarchy = 'date'
    ordering = ['-date']
    inlines = [AttendanceInline]

    # Optional - control form layout
    fieldsets = (
        (None, {
            'fields': ('lecture', 'date','is_makeup_class')
        }),
    )


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'attendance_record', 'attendance_status']
    list_filter = ['attendance_status', 'attendance_record__date']
    search_fields = ['student__user__first_name', 'student__user__last_name']
    autocomplete_fields = ['student', 'attendance_record']
    ordering = ['-attendance_record__date']