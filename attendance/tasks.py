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

@shared_task
def send_daily_attendance_emails():
    logger.info("Starting daily attendance email task")
    try:
        # Get today's date
        today = timezone.now().date()
        # Get all attendance records for today
        attendance_records = AttendanceRecord.objects.filter(date=today).select_related('lecture__lecture_class', 'lecture__course')

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

        # Fetch attendance for each student in the class
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

        # Send emails to each student
        for class_id, data in class_attendances.items():
            for student_id, student_data in data['students'].items():
                student = student_data['student']
                attendances = student_data['attendances']
                if not attendances:
                    continue  # Skip if no attendance records for the student

                subject = f"Daily Attendance Report - {today.strftime('%d/%m/%Y')}"
                message = (
                    f"Hello {student.first_name} {student.last_name},\n\n"
                    f"Here is your attendance status for today ({today.strftime('%d/%m/%Y')}):\n\n"
                )
                for att in attendances:
                    class_type = "Makeup Class" if att['is_makeup'] else "Regular Class"
                    message += f"- {att['course']} ({class_type}): {att['status']}\n"
                message += (
                    "\nPlease contact your teacher or administrator if you have any questions.\n\n"
                    "Best regards,\nThe AttendXMark Team"
                )
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [student.email]

                try:
                    send_mail(
                        subject,
                        message,
                        from_email,
                        recipient_list,
                        fail_silently=False,
                    )
                    logger.info(f"Sent attendance email to {student.email}")
                except Exception as e:
                    logger.error(f"Failed to send email to {student.email}: {str(e)}")

        logger.info("Completed daily attendance email task")
    except Exception as e:
        logger.error(f"Error in daily attendance email task: {str(e)}")