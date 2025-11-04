from .models import * 
def has_role(user, *roles):
    employee = getattr(user, "employee_profile", None)
    if not employee:
        return False

    return employee.role in roles