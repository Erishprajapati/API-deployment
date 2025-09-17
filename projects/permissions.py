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
        obj can be Department or Project.
        Normal employees → only view if they are assigned to a project in this department.
        """
        user_profile = getattr(request.user, "employee_profile", None)
        if not user_profile:
            return False

        # Higher roles → full access
        if user_profile.role in [
            Employee.HR,
            Employee.TEAM_LEAD,
            Employee.PROJECT_MANAGER,
            Employee.ADMIN
        ]:
            return True

        # Normal employee → only view assigned projects/departments
        if request.method in SAFE_METHODS:
            # If obj is a Department
            if hasattr(obj, "projects"):
                assigned_projects = obj.projects.filter(members=user_profile)
                return assigned_projects.exists()
            
            # If obj is a Project
            return (
                user_profile in getattr(obj, "members", [])
                or user_profile == getattr(obj, "manager", None)
                or user_profile == getattr(obj, "team_lead", None)
            )

        return False
