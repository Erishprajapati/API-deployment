from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS, BasePermission
from employee.models import Employee

class IsAssignedEmployeeOrReviewer(permissions.BasePermission):
    """
    Permissions:
    - Assigned employee can submit task for review (status='review')
    - PM / Team Lead / HR / Admin can approve or mark as completed
    """
    def has_object_permission(self, request, view, obj):
        # Always allow safe methods (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Get the employee profile of the logged-in user
        employee = getattr(request.user, "employee_profile", None)
        if not employee:
            return False

        # Case 1: Assigned employee can submit for review
        if obj.assigned_to == employee and request.data.get("status") == "review":
            return True

        # Case 2: PM, Team Lead, HR, or Admin can approve/mark completed
        if employee.role in [
            Employee.PROJECT_MANAGER,
            Employee.TEAM_LEAD,
            Employee.HR,
            Employee.ADMIN
        ]:
            return True

        return False
    


class IsAssignedProjectOrHigher(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user_role = request.user.employeeprofile.role
        return user_role in ['HR', 'TEAM_LEAD', 'PROJECT_MANAGER', 'ADMIN']

    def has_object_permission(self, request, view, obj):
        user_profile = request.user.employeeprofile
        user_role = user_profile.role

        # Higher roles always allowed
        if user_role in ['HR', 'TEAM_LEAD', 'PROJECT_MANAGER', 'ADMIN']:
            return True

        # Normal employee → only view assigned projects
        if request.method in SAFE_METHODS:
            return user_profile in obj.members.all() \
                    or user_profile == obj.manager \
                    or user_profile == obj.team_lead

        return False