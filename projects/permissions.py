from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS, BasePermission
from employee.models import Employee
class IsAssignedEmployeeOrReviewer(permissions.BasePermission):
    """
    Permissions:
    - Assigned employee can submit task for review (status='review')
    - PM / Team Lead / HR / Admin can approve or mark as completed
    """
    def has_permission(self, request, view):
        # Allow read operations for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
            
        employee = getattr(request.user, "employee_profile", None)
        if not employee:
            return False
            
        # Higher roles can perform write operations
        if employee.role in [Employee.PROJECT_MANAGER, Employee.TEAM_LEAD, Employee.HR, Employee.ADMIN]:
            return True
            
        # For write operations, we'll check in has_object_permission
        return True
        
    def has_object_permission(self, request, view, obj):
        employee = getattr(request.user, "employee_profile", None)
        if not employee:
            return False

        # Higher roles → full access
        if employee.role in [Employee.PROJECT_MANAGER, Employee.TEAM_LEAD, Employee.HR, Employee.ADMIN]:
            return True

        # Assigned employee can submit via the submit action
        if view.action == "submit" and obj.assigned_to == employee:
            return True

        # Normal GET/HEAD/OPTIONS access for assigned employee
        if request.method in SAFE_METHODS and obj.assigned_to == employee:
            return True

        return False
    
class IsAssignedProjectOrHigher(BasePermission):
    """
    HR, PM, TL, Admin → full access
    Normal employees → read-only for departments of projects they are assigned to
    """

    def has_permission(self, request, view):
        # Allow anyone to read if GET/HEAD/OPTIONS
        if request.method in SAFE_METHODS:
            return True

        user_profile = getattr(request.user, "employee_profile", None)
        if not user_profile:
            return False

        # Higher roles → full access
        return user_profile.role in [
            Employee.HR,
            Employee.TEAM_LEAD,
            Employee.PROJECT_MANAGER,
            Employee.ADMIN
        ]
    def has_object_permission(self, request, view, obj):
        """
        obj can be a Project or Department
        """
        user_profile = getattr(request.user, "employee_profile", None)
        if not user_profile:
            return False

        # Higher roles → full access
        if user_profile.role in [Employee.HR, Employee.TEAM_LEAD, Employee.PROJECT_MANAGER, Employee.ADMIN]:
            return True

        # Normal employee → only view assigned projects
        if request.method in SAFE_METHODS:
            if hasattr(obj, "members"):  # obj is Project
                return user_profile in obj.members.all()
            if hasattr(obj, "projects"):  # obj is Department
                # only if the employee is assigned to a project in this department
                assigned_projects = obj.projects.filter(members=user_profile)
                return assigned_projects.exists()
        return False


class IsProjectAuthorized(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:   
            return False

        employee = getattr(request.user, "employee_profile", None)
        if not employee:
            return False

        if view.action == "create":
            return employee.role in [Employee.HR, Employee.ADMIN, Employee.PROJECT_MANAGER]

        return True

# class IsProjectAuthorized(permissions.BasePermission):
#     def has_permission(self, request, view):
#         if not request.user.is_authenticated:   
#             return False

#         employee = getattr(request.user, "employee_profile", None)
#         if not employee:
#             return False

#         if view.action == "create":
#             return employee.role in [Employee.HR, Employee.ADMIN, Employee.PROJECT_MANAGER]

#         return True
