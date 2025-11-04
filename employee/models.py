# employee/models.py

from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from multiselectfield import MultiSelectField

User = get_user_model()
"""
Abstract base class for shared fields
"""
class Timestamp(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Department(models.Model):
    name = models.CharField(_('Name'), max_length=50, unique=True, db_index=True)
    description = models.TextField(_('Description'), blank=True, null=True)
    department_code = models.CharField(max_length=100, blank=True)
    working_start_time = models.TimeField(_('Start Time'), default = '09:00')
    working_end_time = models.TimeField(_('End Time'), default = '17:00')
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
class Employee(Timestamp):
    GENDER_CHOICES = [
        ('M', "Male"),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive")
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
    status = models.CharField(max_length=10, choices = STATUS_CHOICES, default = STATUS_ACTIVE, db_index=True)
    role = models.PositiveSmallIntegerField(choices=ROLE_CHOICES, default=EMPLOYEE, db_index=True)
    phone = models.CharField(_('Phone'), max_length=10, validators=[nepali_phone_regex], unique=True)
    dob = models.DateField(_('Date of birth'), null=True, blank=True)
    address = models.TextField(_('Address'), blank=True, null=True)
    gender = models.CharField(_('Gender'), max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    position = models.CharField(_('Position'), max_length=25, blank=True)
    working_start_time = models.TimeField(blank=True, null = True)
    working_end_time = models.TimeField(blank=True, null = True)
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
    # Set working hours from department if not already set
        if self.department:
            if not self.working_start_time:
                self.working_start_time = self.department.working_start_time
            if not self.working_end_time:
                self.working_end_time = self.department.working_end_time

        # Generate employee code if not set
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
    STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("APPROVED", "Approved"),
    ("REJECTED", "Rejected"),
    ("CANCELLED", "Cancelled"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leaves", db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    leave_reason = models.TextField(max_length=255,null=False)
    approved_by = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_leaves")
    approved_at = models.DateTimeField(null=True, blank=True)


    def __str__(self):
        return f"{self.employee} on leave from {self.start_date} to {self.end_date} for {self.leave_reason}"
    
    def clean(self):
        today = timezone.now().date()
        if self.start_date < today:
            raise ValidationError({"start_date": "Start date cannot be in the past."})
        if self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date cannot be before start date."})
        
    @property
    def total_days(self):
        return (self.end_date - self.start_date).days + 1

class WorkingHour(Timestamp):
    department = models.ForeignKey("Department", on_delete=models.CASCADE, related_name="working_hours")

    DAYS_OF_WEEK_CHOICES = [
        ("sunday", "Sunday"),
        ("monday", "Monday"),
        ("tuesday", "Tuesday"),
        ("wednesday", "Wednesday"),
        ("thursday", "Thursday"),
        ("friday", "Friday"),
        ("saturday", "Saturday")
    ]

    days_of_week = MultiSelectField(choices=DAYS_OF_WEEK_CHOICES, default=['monday', 'tuesday', 'wednesday', 'thursday', 'friday'])
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.department.name} - {self.days_of_week}: {self.start_time} to {self.end_time}"

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