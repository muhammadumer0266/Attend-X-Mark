from django.contrib import admin
from .models import Leave, Day, Lecture, AttendanceRecord, Attendance
from django import forms
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.http import Http404

# Register Leave
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

    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        lecture_class = cleaned_data.get('lecture_class')
        
        if course and lecture_class:
            if course.semester != lecture_class.semester:
                self.add_error(None, 
                    f"Warning: Course semester ({course.semester}) doesn't match Class semester ({lecture_class.semester}). "
                    f"This lecture will be automatically marked as 'ended'."
                )
        
        return cleaned_data

@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    form = LectureAdminForm
    list_display = ('course', 'teacher', 'lecture_class', 'start_time', 'end_time', 'days_display', 'status')
    list_filter = ('course', 'teacher', 'lecture_class', 'days', 'status')
    search_fields = ('course__code', 'lecture_class__name', 'teacher__username')
    fields = ('teacher', 'lecture_class', 'course', 'start_time', 'end_time', 'days', 'status')

    def days_display(self, obj):
        return ', '.join(day.name for day in obj.days.all())
    days_display.short_description = 'Days'

    def get_queryset(self, request):
        """
        Override to show all lectures when status filter is applied,
        but only active lectures by default in the changelist view
        """
        qs = super().get_queryset(request)
        # Only filter in changelist view, not in change view
        if hasattr(request, 'resolver_match') and request.resolver_match.url_name == 'attendance_lecture_changelist':
            # If no status filter is applied, show only active lectures
            if 'status__exact' not in request.GET and 'status' not in request.GET:
                return qs.filter(status='active')
        return qs

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Override change_view to handle cases where lecture status changed to 'ended'
        """
        try:
            # Get the object directly from the model without queryset filtering
            obj = Lecture.objects.get(pk=object_id)
            
            # If lecture is ended due to semester mismatch, show a message
            if obj.status == 'ended' and obj.check_semester_mismatch():
                messages.warning(
                    request, 
                    f"This lecture has been automatically marked as 'ended' because the course semester "
                    f"({obj.course.semester}) doesn't match the class semester ({obj.lecture_class.semester})."
                )
            
            return super().change_view(request, object_id, form_url, extra_context)
        
        except Lecture.DoesNotExist:
            # If lecture doesn't exist, redirect to changelist with error message
            messages.error(
                request, 
                f"Lecture with ID '{object_id}' does not exist. It may have been deleted."
            )
            return redirect(reverse('admin:attendance_lecture_changelist'))

    def response_change(self, request, obj):
        """
        Override to handle status changes and provide appropriate messages
        """
        if obj.status == 'ended' and obj.check_semester_mismatch():
            messages.info(
                request,
                f"Lecture status changed to 'ended' due to semester mismatch between "
                f"course ({obj.course.semester}) and class ({obj.lecture_class.semester})."
            )
        
        return super().response_change(request, obj)

    def get_readonly_fields(self, request, obj=None):
        """
        Make status readonly if it's automatically set due to semester mismatch
        """
        readonly_fields = list(super().get_readonly_fields(request, obj))
        
        if obj and obj.status == 'ended' and obj.check_semester_mismatch():
            if 'status' not in readonly_fields:
                readonly_fields.append('status')
                
        return readonly_fields

class AttendanceInline(admin.TabularInline):
    model = Attendance
    extra = 0
    autocomplete_fields = ['student']
    fields = ['student', 'attendance_status']
    readonly_fields = []
    can_delete = True

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['lecture', 'date', 'is_makeup_class', 'lecture_status']
    list_filter = ['date', 'lecture__course', 'lecture__lecture_class', 'is_makeup_class', 'lecture__status']
    search_fields = ['lecture__course__code', 'lecture__lecture_class__name']
    date_hierarchy = 'date'
    ordering = ['-date']
    inlines = [AttendanceInline]

    def lecture_status(self, obj):
        return obj.lecture.status
    lecture_status.short_description = 'Lecture Status'
    lecture_status.admin_order_field = 'lecture__status'

    # Optional - control form layout
    fieldsets = (
        (None, {
            'fields': ('lecture', 'date', 'is_makeup_class')
        }),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Filter lecture choices to only show active lectures
        """
        if db_field.name == "lecture":
            kwargs["queryset"] = Lecture.objects.filter(status='active')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'attendance_record', 'attendance_status', 'lecture_status']
    list_filter = ['attendance_status', 'attendance_record__date', 'attendance_record__lecture__status']
    search_fields = ['student__user__first_name', 'student__user__last_name']
    autocomplete_fields = ['student', 'attendance_record']
    ordering = ['-attendance_record__date']

    def lecture_status(self, obj):
        return obj.attendance_record.lecture.status
    lecture_status.short_description = 'Lecture Status'
    lecture_status.admin_order_field = 'attendance_record__lecture__status'