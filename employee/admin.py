from django.contrib import admin
from .models import *
# Register your models here.
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active')
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone', 'position', 'department')  

    def full_name(self, obj):
        return obj.user.get_full_name() if obj.user else f"Employee {obj.id}"
    full_name.short_description = "Employee"

@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "employee", "profile_photo", "citizenship", "contact_agreement")
    search_fields = ("employee__full_name", "employee__email")  # search by employee info

@admin.register(EmployeeStatus)
class EmployeeStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_active')

# admin.site.register(EmployeeStatus)
@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee','start_date', 'end_date', 'leave_reason')
    # def full_name(self, obj):
    #     return obj.user.get_full_name() if obj.user else f"Employee{obj.id}"
    # full_name.short_description = "Employee"
@admin.register(WorkingHour)
class WorkingHourAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'day_of_week', 'start_time', 'end_time')
@admin.register(EmployeeSchedule)
class EmployeeScheduleAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'availability')