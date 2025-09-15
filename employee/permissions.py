from rest_framework.permissions import BasePermission
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

class IsHRorSuperUser(BasePermission):
    """Allows access only to HR or Admin users."""
    def has_permission(self, request, view):
        return has_role(request.user, Employee.ADMIN, Employee.HR)

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
    
class IsProjectManagerOrSuperUserOrHR(BasePermission):
    """Allows access to Project Manager, HR, or Admin users."""
    def has_permission(self, request, view):
        return has_role(request.user, Employee.PROJECT_MANAGER, Employee.ADMIN, Employee.HR)
    
class IsNotAuthenticatedUser(BasePermission):
    """
    Allows access only to unauthenticated users.
    """
    def has_permission(self, request, view):
        return not request.user or not request.user.is_authenticated
    

class IsSelfOrTeamLeadOrHROrPMOrADMIN(BasePermission):
    """Allow access if logged-in employee is checking their own profile or higher ranked employee"""

    def has_object_permission(self, request, view, obj):
        user = request.user  

        # Higher roles always allowed
        if has_role(user, Employee.HR, Employee.TEAM_LEAD, Employee.PROJECT_MANAGER, Employee.ADMIN):
            return True

        # Normal employee → only their own profile
        return obj.employee.user == user
