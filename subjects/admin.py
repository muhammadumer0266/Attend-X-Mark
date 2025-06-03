from django.contrib import admin
from .models import Semester, Course, DegreeLevel, Discipline, Department, Shift, Section
from django.contrib import messages
from django.db import transaction

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
admin.site.register(Discipline, DisciplineAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Department, DepartmentAdmin)
admin.site.register(Section, SectionAdmin)
admin.site.register(Shift, ShiftAdmin)

from .models import Class

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'semester', 'room_number', 'section', 'degree_level', 'discipline')
    list_filter = ('semester', 'room_number', 'degree_level', 'discipline')
    search_fields = ('name',)
    readonly_fields = ('display_students',)
    actions = ['promote_to_next_semester']

    def display_students(self, obj):
        students = obj.students
        if students.exists():
            return ", ".join(
                f"{student.first_name} {student.last_name} ({student.roll_no or 'No Roll No'})"
                for student in students
            )
        return "No students enrolled"

    display_students.short_description = "Students"

    def get_next_semester(self, current_semester):
        """
        Get the next semester based on current semester name
        Returns None if it's already 8th semester or if next semester doesn't exist
        For 8th semester, returns 'Degree Completed' semester
        """
        # Define semester progression mapping
        semester_progression = {
            '1st Semester': '2nd Semester',
            '2nd Semester': '3rd Semester', 
            '3rd Semester': '4th Semester',
            '4th Semester': '5th Semester',
            '5th Semester': '6th Semester',
            '6th Semester': '7th Semester',
            '7th Semester': '8th Semester',
            '8th Semester': 'Degree Completed'  # Promote 8th semester to Degree Completed
        }
        
        next_semester_name = semester_progression.get(current_semester.name)
        if next_semester_name:
            try:
                return Semester.objects.get(name=next_semester_name)
            except Semester.DoesNotExist:
                return None
        return None

    def get_or_create_degree_completed_semester(self):
        """
        Get or create the 'Degree Completed' semester
        """
        semester, created = Semester.objects.get_or_create(name='Degree Completed')
        return semester, created

    @admin.action(description='Promote selected classes to next semester')
    def promote_to_next_semester(self, request, queryset):
        """
        Admin action to promote selected classes to the next semester
        For 8th semester classes, promotes students to 'Degree Completed'
        """
        promoted_count = 0
        graduated_count = 0
        missing_next_semester_count = 0
        error_count = 0
        degree_completed_created = False
        
        with transaction.atomic():
            for class_obj in queryset:
                try:
                    current_semester = class_obj.semester
                    if not current_semester:
                        messages.warning(
                            request, 
                            f"Class '{class_obj.name}' has no semester assigned. Skipped."
                        )
                        continue
                    
                    # Special handling for 8th semester - promote students to "Degree Completed"
                    if current_semester.name == '8th Semester':
                        # Get or create the "Degree Completed" semester
                        degree_completed_semester, created = self.get_or_create_degree_completed_semester()
                        if created and not degree_completed_created:
                            degree_completed_created = True
                            messages.info(
                                request,
                                "Created 'Degree Completed' semester in the database."
                            )
                        
                        # Get students in this class before updating
                        students_in_class = list(class_obj.students)
                        student_count = len(students_in_class)
                        
                        # Update the class semester to "Degree Completed"
                        old_semester_name = current_semester.name
                        class_obj.semester = degree_completed_semester
                        class_obj.save()
                        
                        graduated_count += 1
                        
                        # Log the graduation
                        messages.success(
                            request,
                            f"Class '{class_obj.name}' completed degree! {student_count} student(s) moved from {old_semester_name} to Degree Completed."
                        )
                        
                        continue
                    
                    # Handle regular semester progression (1st to 7th semester)
                    next_semester = self.get_next_semester(current_semester)
                    
                    if next_semester:
                        # Store old semester for logging
                        old_semester_name = current_semester.name
                        
                        # Update the class semester
                        class_obj.semester = next_semester
                        class_obj.save()
                        
                        promoted_count += 1
                        
                        # Log the promotion
                        messages.success(
                            request,
                            f"Class '{class_obj.name}' promoted from {old_semester_name} to {next_semester.name}"
                        )
                        
                    else:
                        missing_next_semester_count += 1
                        messages.error(
                            request,
                            f"Next semester for '{class_obj.name}' (currently {current_semester.name}) doesn't exist in the database."
                        )
                
                except Exception as e:
                    error_count += 1
                    messages.error(
                        request,
                        f"Error promoting class '{class_obj.name}': {str(e)}"
                    )
        
        # Summary message
        summary_parts = []
        if promoted_count > 0:
            summary_parts.append(f"{promoted_count} class(es) successfully promoted to next semester")
        if graduated_count > 0:
            summary_parts.append(f"{graduated_count} class(es) completed their degree")
        if missing_next_semester_count > 0:
            summary_parts.append(f"{missing_next_semester_count} class(es) couldn't be promoted due to missing next semester")
        if error_count > 0:
            summary_parts.append(f"{error_count} class(es) had errors during promotion")
        
        if summary_parts:
            messages.info(request, "Promotion Summary: " + ", ".join(summary_parts))
        
        # Additional info about student updates
        total_processed = promoted_count + graduated_count
        if total_processed > 0:
            messages.info(
                request,
                f"Note: Students in promoted/graduated classes will be automatically updated to the new semester."
            )
            
        # Special message for degree completion
        if graduated_count > 0:
            messages.success(
                request,
                f"🎓 Congratulations! {graduated_count} class(es) have completed their degree program!"
            )