from django.contrib import admin
from .models import Semester, Course, DegreeLevel, Discipline, Department, Shift, Section, Class
from django.contrib import messages
from django.db import transaction
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

def get_promotion_email_template(first_name, last_name, old_semester, new_semester):
    """Generate HTML email template for promotion or degree completion."""
    
    # Title & body message
    if new_semester.name == "Degree Completed":
        heading = "🎓 Degree Completed"
        message = f"Congratulations <strong>{first_name}  {last_name}</strong>! 🎉<br><br>You have successfully completed your degree. Wishing you the best in your future career!"
    else:
        heading = "🎉 Promotion Update"
        message = f"Congratulations <strong>{first_name} {last_name}</strong>! 🎉<br><br>You have been promoted from <strong>{old_semester.name}</strong> to <strong>{new_semester.name}</strong>. Keep up the great work!"

    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Promotion Update - AttendXMark</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    </head>
    <body style="font-family: 'Poppins', Arial, sans-serif; background-color: #E0EAF2; color: #1d3557; margin: 0; padding: 0;">
        <div style="max-width: 600px; margin: 40px auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 25px rgba(29, 53, 87, 0.1);">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #457b9d 0%, #1d3557 100%); padding: 30px; text-align: center; color: #fff;">
                <h1 style="margin: 0; font-size: 23px;">{heading}</h1>
            </div>
            
            <!-- Content -->
            <div style="padding: 30px;">
                <h2 style="text-align: center; font-size: 22px; margin-bottom: 20px;">
                    Hello <span style="color: #457b9d;">{first_name}  {last_name}</span>!
                </h2>
                <p style="margin-bottom: 20px; font-size: 15px; line-height: 1.6;">
                    {message}
                </p>
            </div>

            <!-- Footer -->
            <div style="background: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #E0EAF2;">
                <p style="margin: 0; font-size: 14px; color: #457b9d;">
                    Thank you for choosing <span style="font-weight: 600; color: #1d3557;">AttendXMark</span>
                </p>
                <p style="margin: 0; font-size: 13px; color: #78909c;">
                    A Smart attendance solution.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_template


def send_promotion_email(student, old_semester, new_semester):
    subject = "🎓 Promotion Update"
    from_email = "attendxmark@gmail.com"
    recipient_list = [student.email]

    # Get HTML template
    html_message = get_promotion_email_template(student.first_name,student.last_name, old_semester, new_semester)

    # Plain text fallback
    plain_message = strip_tags(html_message)

    msg = EmailMultiAlternatives(subject, plain_message, from_email, recipient_list)
    msg.attach_alternative(html_message, "text/html")
    msg.send()



# =========================
# Admin Configurations
# =========================

class SemesterAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

class DegreeLevelAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

class DisciplineAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'code', 'semester', 'degree_level', 'discipline']
    list_filter = ['semester', 'degree_level', 'discipline']
    search_fields = ['title', 'code']
    ordering = ['semester', 'code']

class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

class ShiftAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

class SectionAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

# Register Models
admin.site.register(Semester, SemesterAdmin)
admin.site.register(DegreeLevel, DegreeLevelAdmin)
admin.site.register(Discipline, DisciplineAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Department, DepartmentAdmin)
admin.site.register(Section, SectionAdmin)
admin.site.register(Shift, ShiftAdmin)


# =========================
# Class Admin
# =========================
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
        semester_progression = {
            '1st Semester': '2nd Semester',
            '2nd Semester': '3rd Semester', 
            '3rd Semester': '4th Semester',
            '4th Semester': '5th Semester',
            '5th Semester': '6th Semester',
            '6th Semester': '7th Semester',
            '7th Semester': '8th Semester',
            '8th Semester': 'Degree Completed'
        }
        
        next_semester_name = semester_progression.get(current_semester.name)
        if next_semester_name:
            try:
                return Semester.objects.get(name=next_semester_name)
            except Semester.DoesNotExist:
                return None
        return None

    def get_or_create_degree_completed_semester(self):
        semester, created = Semester.objects.get_or_create(name='Degree Completed')
        return semester, created

    @admin.action(description='Promote selected classes to next semester')
    def promote_to_next_semester(self, request, queryset):
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
                        messages.warning(request, f"Class '{class_obj.name}' has no semester assigned. Skipped.")
                        continue
                    
                    # Handle 8th Semester → Degree Completed
                    if current_semester.name == '8th Semester':
                        degree_completed_semester, created = self.get_or_create_degree_completed_semester()
                        if created and not degree_completed_created:
                            degree_completed_created = True
                            messages.info(request, "Created 'Degree Completed' semester in the database.")
                        
                        students_in_class = list(class_obj.students)
                        student_count = len(students_in_class)
                        
                        old_semester_name = current_semester.name
                        class_obj.semester = degree_completed_semester
                        class_obj.save()
                        
                        # 📧 Send degree completion emails
                        for student in students_in_class:
                            if student.email:
                                send_promotion_email(student, current_semester, degree_completed_semester)
                        
                        graduated_count += 1
                        messages.success(request, f"Class '{class_obj.name}' completed degree! {student_count} student(s) moved from {old_semester_name} to Degree Completed.")
                        continue
                    
                    # Handle 1st → 7th Semester
                    next_semester = self.get_next_semester(current_semester)
                    
                    if next_semester:
                        students_in_class = list(class_obj.students)
                        old_semester_name = current_semester.name
                        
                        class_obj.semester = next_semester
                        class_obj.save()
                        
                        # 📧 Send promotion emails
                        for student in students_in_class:
                            if student.email:
                                send_promotion_email(student, current_semester, next_semester)
                        
                        promoted_count += 1
                        messages.success(request, f"Class '{class_obj.name}' promoted from {old_semester_name} to {next_semester.name}")
                    else:
                        missing_next_semester_count += 1
                        messages.error(request, f"Next semester for '{class_obj.name}' (currently {current_semester.name}) doesn't exist in the database.")
                
                except Exception as e:
                    error_count += 1
                    messages.error(request, f"Error promoting class '{class_obj.name}': {str(e)}")
        
        # Summary
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
        
        if (promoted_count + graduated_count) > 0:
            messages.info(request, "Note: Students in promoted/graduated classes have been automatically updated and notified via email.")
        if graduated_count > 0:
            messages.success(request, f"🎓 Congratulations! {graduated_count} class(es) have completed their degree program!")
