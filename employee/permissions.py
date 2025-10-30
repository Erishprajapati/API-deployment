from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import Employee

def get_employee_role(user):
    """
    Return the role of the employee if user is authenticated, else None.
    """
    if not user or not user.is_authenticated:
        return None
    try:
        return user.employee_profile.role
    except (Employee.DoesNotExist, AttributeError):
        return None

def has_role(user, *roles):
    """Check if user has one of the given roles."""
    return get_employee_role(user) in roles

class IsProjectManager(BasePermission):
    """Allows access only to Project Manager users."""
    def has_permission(self, request, view):
        return has_role(request.user, Employee.PROJECT_MANAGER)

class IsTeamLead(BasePermission):
    """Allows access only to Team Lead users."""
    def has_permission(self, request, view):
        return has_role(request.user, Employee.TEAM_LEAD)

class IsEmployee(BasePermission):
    """Allows access only to general Employee users."""
    def has_permission(self, request, view):
        return has_role(request.user, Employee.EMPLOYEE)
class IsHROrAdminOrProjectManager(BasePermission):
    """
    Allows access only to users who are HR, Admin, or Project Manager.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        employee = getattr(request.user, 'employee_profile', None)
        if not employee:
            return False

        return employee.role in [Employee.HR, Employee.ADMIN, Employee.PROJECT_MANAGER]
class IsNotAuthenticatedUser(BasePermission):
    """
    Allows access only to unauthenticated users.
    """
    def has_permission(self, request, view):
        return not request.user or not request.user.is_authenticated
    
class IsSelfOrTeamLeadOrHROrPMOrADMIN(BasePermission):
    """Allow access if higher ranked employee, assigned employee, or comment author"""

    def has_object_permission(self, request, view, obj):
        user = request.user
        employee = getattr(user, "employee_profile", None)

        if employee is None:
            return False

        # Higher roles → full access
        if has_role(user, Employee.HR, Employee.TEAM_LEAD, Employee.PROJECT_MANAGER, Employee.ADMIN):
            return True

        # Assigned employee can access
        if hasattr(obj, "task") and obj.task.assigned_to == employee:
            return True

        # Comment author can access
        if hasattr(obj, "author") and obj.author == employee:
            return True

        # EmployeeProfile object check
        if hasattr(obj, "employee") and obj.employee == employee:
            return True

        return False