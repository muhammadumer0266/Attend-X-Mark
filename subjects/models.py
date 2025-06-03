from django.db import models
# from accounts.models import Student

# Semester Model
class Semester(models.Model):
    name = models.CharField(max_length=50, unique=True)  # e.g., 1st Semester, 2nd Semester

    def __str__(self):
        return self.name


# Degree Level Model
class DegreeLevel(models.Model):
    name = models.CharField(max_length=50, unique=True)  # e.g., BS, MS

    def __str__(self):
        return self.name


# discipline Model
class Discipline(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g., IT, CS, SE

    def __str__(self):
        return self.name


# Course Model
class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name="courses")
    degree_level = models.ForeignKey(DegreeLevel, on_delete=models.CASCADE, related_name="courses")
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE, related_name="courses")
    credit_hours = models.PositiveIntegerField(default=3)

    def __str__(self):
        return f"{self.code} - {self.title}"


# Department Model
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g., Computer Science Department

    def __str__(self):
        return self.name
    
class Shift(models.Model):
    name = models.CharField(max_length=20, unique=True)
    def __str__(self):
        return self.name
class Section(models.Model):
    name = models.CharField(max_length=20, unique=True)
    def __str__(self):
        return self.name

from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from subjects.models import Shift, Section, DegreeLevel, Discipline, Semester, Department

# Class Model
class Class(models.Model):
    room_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="The room number where the class is held (e.g., B-101)"
    )
    session = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        help_text="The session of the class (e.g., 21 - 25)"
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='classes',
        help_text="The section of the class (e.g., A, B, C)"
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classes'
    )
    degree_level = models.ForeignKey(
        DegreeLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    discipline = models.ForeignKey(
        Discipline,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classes'
    )
    name = models.CharField(
        max_length=255,
        help_text="The name or code of the class (e.g., 'Mathematics 101')"
    )

    class Meta:
        verbose_name = "Class"
        verbose_name_plural = "Classes"
        unique_together = ('name', 'section', 'semester')

    def __str__(self):
        section = self.section if self.section else "No Section"
        return f"{self.degree_level}{self.discipline} {self.semester} {self.shift} - Section {section} (Session {self.session})"

    @property
    def students(self):
        from accounts.models import Student
        return Student.objects.filter(
            section=self.section,
            semester=self.semester,
            shift=self.shift,
            degree_level=self.degree_level,
            discipline=self.discipline
        )

# Store the old semester value before saving
@receiver(pre_save, sender=Class)
def store_old_semester(sender, instance, **kwargs):
    if instance.pk:  # Check if this is an update (not a creation)
        try:
            old_instance = Class.objects.get(pk=instance.pk)
            instance._old_semester = old_instance.semester
        except Class.DoesNotExist:
            instance._old_semester = None
    else:
        instance._old_semester = None

# Update students' semester after the class semester changes
@receiver(post_save, sender=Class)
def update_students_semester(sender, instance, created, **kwargs):
    if created:
        return  # Do nothing on creation

    # Check if semester has changed
    old_semester = getattr(instance, '_old_semester', None)
    if old_semester != instance.semester:
        from accounts.models import Student
        # Find students with the old semester and matching other fields
        students = Student.objects.filter(
            section=instance.section,
            semester=old_semester,  # Match the old semester
            shift=instance.shift,
            degree_level=instance.degree_level,
            discipline=instance.discipline
        )
        if students.exists():
            students.update(semester=instance.semester)