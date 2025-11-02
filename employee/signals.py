from .models import Employee, EmployeeProfile, EmployeeSchedule, Leave, Department
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete

@receiver(post_save, sender=Employee)
def create_employee_profile(sender, instance, created, **kwargs):
    if created:
        # Create profile for the new employee
        EmployeeProfile.objects.create(employee=instance)


@receiver([post_save, post_delete], sender=Leave)
def update_employee_schedule(sender, instance, **kwargs):
    employee = instance.employee
    if not employee:
        return  # Safety check in case employee is None

    # Get or create the schedule
    schedule, created = EmployeeSchedule.objects.get_or_create(employee=employee)

    # Update availability based on current leaves
    schedule.update_availability()
"""this code handles the changes the department information(name) are updated"""
@receiver(post_save, sender = Department)
def update_employee_codes(sender, instance,created, **kwargs):
    if created:
        return #this code skips new department
    
    """checking if the name is actually changed or not"""
    old_instance = sender.objects.filter(pk = instance.pk).first()
    if not old_instance:
        return
    
    if old_instance != instance.name:
        """generate new department code based on new name"""
        prefix = instance.name[:3].upper()
        numeric_part = instance.department_code[:3] if instance.department_code else "001" #deafult as 001
        new_dept_code = f"{prefix}{numeric_part}"

        if instance.department_code != new_dept_code:
            sender.objects.filter(pk = instance.pk).update(department_code = new_dept_code)
            """updating all the employees in this section"""
            employees = instance.employees.all()
            for emp in employees:
                if emp.date_of_joining:
                    date_part = emp.date_of_joining.strftime("%Y%m")
                    seq = emp.employee_code.split('-')[-1] if emp.employee_code else "001"
                    emp.employee_code = f"{new_dept_code}-{date_part}-{seq}"
                    emp.save(update_fields=["employee_code"])

@receiver(post_save, sender=Department)
def update_employee_hours(sender, instance, **kwargs):
    instance.employees.update(
        working_start_time=instance.working_start_time,
        working_end_time=instance.working_end_time
    )