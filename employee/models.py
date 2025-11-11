# employee/models.py
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from multiselectfield import MultiSelectField
from datetime import datetime, time, timedelta

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
    def clean(self):
        if self.working_start_time and self.working_end_time:
            if self.working_start_time == self.working_end_time:
                raise ValidationError("Start and end time must be different.")
            
            duration = self.get_shift_duration()
            max_duration = 8 * 3600
            if duration.total_seconds() > max_duration:
                hours = duration.total_seconds() / 3600
                raise ValidationError(
                    f"Shift duration ({hours:.1f} hours) exceeds the maximum allowed (8 hours)."
                )

    def get_shift_duration(self) -> timedelta:
        start = self.working_start_time
        end = self.working_end_time
        if not (start and end):
            return timedelta(0)

        dummy = datetime.today()
        start_dt = datetime.combine(dummy, start)
        end_dt = datetime.combine(dummy, end)
        if end <= start:
            end_dt += timedelta(days=1)
        return end_dt - start_dt

    def is_on_shift(self, now: datetime = None) -> bool:
        if not self.is_active:
            return False

        if not (self.working_start_time and self.working_end_time):
            return False

        if now is None:
            now = timezone.now()
        now_time = timezone.localtime(now).time()
        start, end = self.working_start_time, self.working_end_time

        if start <= end:
            return start <= now_time <= end
        else:
            return now_time >= start or now_time <= end
        
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.department_code:
            prefix = self.name[:3].upper()
            with transaction.atomic():
                last_dept = Department.objects.select_for_update().order_by('-id').first()
                next_num = (last_dept.id + 1) if last_dept else 1
                self.department_code = f"{prefix}{next_num:03d}"
        super().save(*args, **kwargs)

# Validation for Nepali phone numbers
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
    ('off_shift', 'Off Shift'),  # ← Better than "busy" for non-working hours
    ]
    employee = models.OneToOneField(Employee, on_delete=models.SET_NULL, null = True, blank = True)
    availability = models.CharField(max_length=20,choices = STATUS_CHOICES, default="available")
    def update_availability(self):
        if not self.employee or not self.employee.department:
            self.availability = "off_shift"
            self.save(update_fields=["availability"])
            return

        now = timezone.now()
        today_nepal = timezone.localtime(now).date()
        current_time_nepal = timezone.localtime(now).time()

        """check if there is any approved leave for employee"""
        on_approved_leave = Leave.objects.filter(
            employee=self.employee,
            status="APPROVED",
            start_date__lte=today_nepal,
            end_date__gte=today_nepal
        ).exists()
        if on_approved_leave:
            self.availability = "on_leave"
            self.save(update_fields=["availability"])
            return
        """first check if the department working time is available or not"""
        dept = self.employee.department
        if not (dept.working_start_time and dept.working_end_time):
            self.availability = "off_shift"
            self.save(update_fields=["availability"])
            return

        start = dept.working_start_time
        end = dept.working_end_time

        if start <= end:
            is_working_hour = start <= current_time_nepal <= end
        else:
            is_working_hour = current_time_nepal >= start or current_time_nepal <= end

        self.availability = "available" if is_working_hour else "off_shift"
        self.save(update_fields=["availability"])

    def __str__(self):
        if self.employee:
            return f"{self.employee.user.get_full_name()} - {self.availability}"
        return f"Unassigned Schedule - {self.availability}"