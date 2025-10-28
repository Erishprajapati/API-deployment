# employee/models.py

from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.utils import timezone
from django.core.exceptions import ValidationError

User = get_user_model()

"""
Abstract base class for shared fields
"""
class Timestamp(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class Department(models.Model):
    name = models.CharField(_('Name'), max_length=50, unique=True, db_index=True)
    description = models.TextField(_('Description'), blank=True, null=True)
    department_code = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.department_code:
            prefix = self.name[:3].upper()
            last_count = Department.objects.count() + 1
            self.department_code = f"{prefix}{last_count:03d}"
        super().save(*args, **kwargs)



# Validator for Nepali phone numbers
nepali_phone_regex = RegexValidator(
    regex=r'^9[6-8]\d{8}$',
    message=_("Kindly enter valid phone numbers")
)

class EmployeeStatus(Timestamp):
    is_active = models.BooleanField(_('Status'), default=True)

    def __str__(self):
        return "Active" if self.is_active else "Inactive"
class Employee(Timestamp):
    GENDER_CHOICES = [
        ('M', "Male"),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    # Role choices
    HR = 1
    PROJECT_MANAGER = 2
    TEAM_LEAD = 3
    EMPLOYEE = 4
    ADMIN = 5

    ROLE_CHOICES = [
        (HR, 'HR'),
        (PROJECT_MANAGER, 'Project Manager'),
        (TEAM_LEAD, 'Team Lead'),
        (EMPLOYEE, 'Employee'),
        (ADMIN, 'Admin'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        related_name='employee_profile',
        null=True,
        blank=True
    )
    role = models.PositiveSmallIntegerField(choices=ROLE_CHOICES, default=EMPLOYEE, db_index=True)
    phone = models.CharField(_('Phone'), max_length=10, validators=[nepali_phone_regex], unique=True)
    dob = models.DateField(_('Date of birth'), null=True, blank=True)
    address = models.TextField(_('Address'), blank=True, null=True)
    gender = models.CharField(_('Gender'), max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    position = models.CharField(_('Position'), max_length=25, blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        db_index=True
    )
    skills = models.JSONField(_('Skills'), default=list, blank=True)
    date_of_joining = models.DateTimeField(null=False, blank=False, db_index=True)  # Set at signup
    employee_code = models.CharField(
        max_length=255,
        unique=True,
        null=True,   # Critical: use NULL instead of "" to avoid unique constraint issues
        blank=True
    )

    def __str__(self):
        return self.user.get_full_name() if self.user else f"Employee {self.id}"

    def save(self, *args, **kwargs):
        # Only generate code if not already set, and department/date are available
        if not self.employee_code and self.department and self.date_of_joining:
            with transaction.atomic():
                existing_count = Employee.objects.filter(
                    department=self.department,
                    date_of_joining__year=self.date_of_joining.year,
                    date_of_joining__month=self.date_of_joining.month,
                ).select_for_update().count()

                dept_code = self.department.name[:3].upper()
                date_part = self.date_of_joining.strftime("%Y%m")
                self.employee_code = f"{dept_code}-{date_part}-{existing_count + 1:03d}"

        super().save(*args, **kwargs)

    @property
    def schedule(self):
        try:
            return self.employeeschedule
        except EmployeeSchedule.DoesNotExist:
            return None

class EmployeeProfile(Timestamp):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='profile')
    profile_photo = models.FileField(upload_to='employee/profile/profile_photo/', null=True, blank=True)
    citizenship = models.FileField(upload_to='employee/profile/citizenship/', blank=True, null=True)
    contact_agreement = models.FileField(upload_to='employee/profile/contactagreement/', null=True, blank=True)

    def __str__(self):
        return str(self.employee)
    
class Leave(Timestamp):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leaves", db_index=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    leave_reason = models.TextField()

    def __str__(self):
        return f"{self.employee} on leave from {self.start_date} to {self.end_date} for {self.leave_reason}"
    
    def clean(self):
        today = timezone.now().date()
        """start date cannot be in past"""
        if self.start_date<today:
            raise ValidationError({"Start Date" : "Start date can not be in past time"})
        if self.end_date<today:
            raise ValidationError({"end_date": "End date cannot be before start date."})
        
class WorkingHour(Timestamp):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="working_hours")
    day_of_week = models.CharField(
        max_length = 10,
        choices = [
            ("sunday", "Sunday"),
            ("monday", "Monday"),
            ("tuesday", "Tuesday"),
            ("wednesday", "Wednesday"),
            ("thursday", "Thursday"),
            ("friday", "Friday"),
            ("saturday", "Saturday")
        ],
    )

    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.employee} - {self.day_of_week}: {self.start_time} to {self.end_time}"
    
class EmployeeSchedule(Timestamp):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('on_leave', 'On Leave'),
        ('busy', 'Busy')
    ]
    employee = models.OneToOneField(Employee, on_delete=models.SET_NULL, null = True, blank = True)
    availability = models.CharField(max_length=20,choices = STATUS_CHOICES, default="available")

    
    def update_availability(self):
        today = timezone.now()
        active_leave = self.employee.leaves.filter(
            start_date__lte = today,
            end_date__gte = today
        ).exists()

        if active_leave:
            self.availability = "on_leave"
        else:
            self.availability = "available"

        self.save(update_fields=["availability"])

    def __str__(self):
        if self.employee:
            return f"{self.employee.user.get_full_name()} - {self.availability}"
        return f"Unassigned Schedule - {self.availability}"