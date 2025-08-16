from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import Attendance, AttendanceRecord, Leave
from accounts.models import Student
import logging

logger = logging.getLogger(__name__)

@shared_task
def update_attendance_on_leave_approval(leave_id):
    logger.info(f"Processing leave ID {leave_id}")
    try:
        leave = Leave.objects.get(id=leave_id)
        logger.info(f"Leave found: {leave.user.email}, status: {leave.status}")
        if leave.status == 'Approved':
            attendance_record = AttendanceRecord.objects.filter(
                lecture=leave.lecture,
                date=leave.leave_date,
            ).first()
            if attendance_record:
                student = Student.objects.get(id=leave.user.id)
                attendance = Attendance.objects.filter(
                    attendance_record=attendance_record,
                    student=student
                ).first()
                if attendance and attendance.attendance_status == 'absent':
                    attendance.attendance_status = 'leave'
                    attendance.save()
                    logger.info(f"Updated attendance for {student.roll_no} to 'leave' for {leave.leave_date}")
                else:
                    logger.info(f"No update needed: Attendance for {student.roll_no} is {attendance.attendance_status if attendance else 'not found'}")
            else:
                logger.warning(f"No attendance record found for lecture {leave.lecture} on {leave.leave_date}")
        else:
            logger.info(f"Leave ID {leave_id} not approved, status: {leave.status}")
    except Leave.DoesNotExist:
        logger.error(f"Leave ID {leave_id} does not exist")
    except Student.DoesNotExist:
        logger.error(f"Student for leave ID {leave_id} does not exist")

from celery import shared_task
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from .models import Attendance, AttendanceRecord, Leave
from accounts.models import Student
import logging

logger = logging.getLogger(__name__)


@shared_task
def update_attendance_on_leave_approval(leave_id):
    """Update attendance status when leave is approved."""
    logger.info(f"Processing leave ID {leave_id}")
    try:
        leave = Leave.objects.get(id=leave_id)
        logger.info(f"Leave found: {leave.user.email}, status: {leave.status}")
        if leave.status == 'Approved':
            attendance_record = AttendanceRecord.objects.filter(
                lecture=leave.lecture,
                date=leave.leave_date,
            ).first()
            if attendance_record:
                student = Student.objects.get(id=leave.user.id)
                attendance = Attendance.objects.filter(
                    attendance_record=attendance_record,
                    student=student
                ).first()
                if attendance and attendance.attendance_status == 'absent':
                    attendance.attendance_status = 'leave'
                    attendance.save()
                    logger.info(f"Updated attendance for {student.roll_no} to 'leave' for {leave.leave_date}")
                else:
                    logger.info(
                        f"No update needed: Attendance for {student.roll_no} is "
                        f"{attendance.attendance_status if attendance else 'not found'}"
                    )
            else:
                logger.warning(f"No attendance record found for lecture {leave.lecture} on {leave.leave_date}")
        else:
            logger.info(f"Leave ID {leave_id} not approved, status: {leave.status}")
    except Leave.DoesNotExist:
        logger.error(f"Leave ID {leave_id} does not exist")
    except Student.DoesNotExist:
        logger.error(f"Student for leave ID {leave_id} does not exist")


# ---------------- EMAIL TEMPLATE ---------------- #

def get_daily_attendance_email_template(first_name, last_name, date, attendances):
    """Generate HTML email template for daily attendance report."""
    attendance_rows = ""
    for att in attendances:
        class_type = "Makeup Class" if att['is_makeup'] else "Regular Class"
        attendance_rows += f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #E0EAF2;">{att['course']}</td>
                <td style="padding: 8px; border: 1px solid #E0EAF2;">{class_type}</td>
                <td style="padding: 8px; border: 1px solid #E0EAF2; font-weight: 600; 
                           color: {'#28a745' if att['status'] == 'Present' else '#e63946'};">
                    {att['status']}
                </td>
            </tr>
        """

    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Daily Attendance Report - AttendXMark</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    </head>
    <body style="font-family: 'Poppins', Arial, sans-serif; background-color: #E0EAF2; color: #1d3557; margin: 0; padding: 0;">
        <div style="max-width: 600px; margin: 40px auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 25px rgba(29, 53, 87, 0.1);">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #457b9d 0%, #1d3557 100%); padding: 30px; text-align: center; color: #fff;">
                <h1 style="margin: 0; font-size: 26px;">📊 Daily Attendance Report</h1>
                <p style="margin: 5px 0 0; font-size: 14px;">Date: {date}</p>
            </div>
            
            <!-- Content -->
            <div style="padding: 30px;">
                <h2 style="text-align: center; font-size: 22px; margin-bottom: 20px;">
                    Hello <span style="color: #457b9d;">{first_name} {last_name}</span>!
                </h2>
                <p style="margin-bottom: 15px;">Here is your attendance summary for today:</p>
                
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                    <thead>
                        <tr style="background-color: #f1f5f9;">
                            <th style="padding: 10px; border: 1px solid #E0EAF2; text-align: left;">Course</th>
                            <th style="padding: 10px; border: 1px solid #E0EAF2; text-align: left;">Class Type</th>
                            <th style="padding: 10px; border: 1px solid #E0EAF2; text-align: left;">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {attendance_rows}
                    </tbody>
                </table>

                <p style="margin-top: 10px; font-size: 14px; color: #1d3557;">
                    Please contact your teacher or administrator if you have any questions.
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


# ---------------- DAILY EMAIL SENDER ---------------- #

@shared_task
def send_daily_attendance_emails():
    """Send daily attendance summary emails to all students."""
    logger.info("Starting daily attendance email task")
    try:
        today = timezone.now().date()
        attendance_records = AttendanceRecord.objects.filter(date=today).select_related(
            'lecture__lecture_class', 'lecture__course'
        )

        # Group attendance records by class
        class_attendances = {}
        for record in attendance_records:
            class_instance = record.lecture.lecture_class
            if class_instance:
                if class_instance.id not in class_attendances:
                    class_attendances[class_instance.id] = {
                        'class': class_instance,
                        'students': {},
                        'lectures': set()
                    }
                class_attendances[class_instance.id]['lectures'].add(record.lecture.lecture_id)

        # Fetch attendance for each student
        for class_id, data in class_attendances.items():
            class_instance = data['class']
            students = class_instance.students.all()
            for student in students:
                student_attendances = Attendance.objects.filter(
                    attendance_record__in=attendance_records,
                    student=student
                ).select_related('attendance_record__lecture__course')
                attendance_summary = []
                for attendance in student_attendances:
                    attendance_summary.append({
                        'course': attendance.attendance_record.lecture.course.title,
                        'status': attendance.attendance_status.capitalize(),
                        'is_makeup': attendance.attendance_record.is_makeup_class
                    })
                class_attendances[class_id]['students'][student.id] = {
                    'student': student,
                    'attendances': attendance_summary
                }

        # Send emails
        for class_id, data in class_attendances.items():
            for student_id, student_data in data['students'].items():
                student = student_data['student']
                attendances = student_data['attendances']
                if not attendances:
                    continue  

                subject = f"Daily Attendance Report - {today.strftime('%d/%m/%Y')}"
                plain_message = f"Hello {student.first_name} {student.last_name},\n\nHere is your attendance status for today ({today.strftime('%d/%m/%Y')}):\n\n"
                for att in attendances:
                    class_type = "Makeup Class" if att['is_makeup'] else "Regular Class"
                    plain_message += f"- {att['course']} ({class_type}): {att['status']}\n"
                plain_message += "\nPlease contact your teacher or administrator if you have any questions.\n\nBest regards,\nThe AttendXMark Team"

                html_message = get_daily_attendance_email_template(
                    student.first_name, student.last_name, today.strftime('%d/%m/%Y'), attendances
                )

                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [student.email]

                try:
                    msg = EmailMultiAlternatives(subject, plain_message, from_email, recipient_list)
                    msg.attach_alternative(html_message, "text/html")  # ✅ Correct way
                    msg.send()
                    logger.info(f"Sent attendance email to {student.email}")
                except Exception as e:
                    logger.error(f"Failed to send email to {student.email}: {str(e)}")

        logger.info("Completed daily attendance email task")
    except Exception as e:
        logger.error(f"Error in daily attendance email task: {str(e)}")
