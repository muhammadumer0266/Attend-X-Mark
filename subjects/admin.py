from django.contrib import admin
from .models import Semester, Course, DegreeLevel, Discipline,Department,Shift,Section


# Semester Admin
class SemesterAdmin(admin.ModelAdmin):
    list_display = ['name']  # Display semester name in admin panel
    search_fields = ['name']  # Add search functionality


# Degree Level Admin
class DegreeLevelAdmin(admin.ModelAdmin):
    list_display = ['name']  # Display degree level name
    search_fields = ['name']  # Add search functionality


# discipline Admin
class DisciplineAdmin(admin.ModelAdmin):
    list_display = ['name']  # Display discipline name
    search_fields = ['name']  # Add search functionality


# Course Admin
class CourseAdmin(admin.ModelAdmin):
    # Display the course details in a tabular format
    list_display = ['title', 'code', 'semester', 'degree_level', 'discipline']  # Columns displayed
    list_filter = ['semester', 'degree_level', 'discipline']  # Filter options
    search_fields = ['title', 'code']  # Search by title or code
    ordering = ['semester', 'code']  # Order by semester first, then code



# discipline Admin
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name']  # Display discipline name
    search_fields = ['name']  # Add search functionality
    
# discipline Admin
class ShiftAdmin(admin.ModelAdmin):
    list_display = ['name']  # Display discipline name
    search_fields = ['name']  # Add search functionality
    
# discipline Admin
class SectionAdmin(admin.ModelAdmin):
    list_display = ['name']  # Display discipline name
    search_fields = ['name']  # Add search functionality



# Register Models with Custom Admin Classes
admin.site.register(Semester, SemesterAdmin)
admin.site.register(DegreeLevel, DegreeLevelAdmin)
admin.site.register(Discipline,DisciplineAdmin)

admin.site.register(Course, CourseAdmin)
admin.site.register(Department,DepartmentAdmin)
admin.site.register(Section,SectionAdmin)
admin.site.register(Shift,ShiftAdmin)
# admin.site.register(Shift,ShiftAdmin)


from.models import Class

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'semester', 'room_number', 'section')
    list_filter = ('semester', 'room_number')
    search_fields = ('name',)
    readonly_fields = ('display_students',)

    def display_students(self, obj):
        students = obj.students
        if students.exists():
            return ", ".join(
                f"{student.first_name} {student.last_name} ({student.roll_no or 'No Roll No'})"
                for student in students
            )
        return "No students enrolled"

    display_students.short_description = "Students"