from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from employee.models import *
from datetime import timedelta

class DepartmentModelTest(TestCase):
    def test_create_department_generates_code(self):
        dept = Department.objects.create(name="Development Team")
        self.assertTrue(dept.department_code.startswith("DEV"))
        self.assertEqual(str(dept), "Development Team")
    
    def test_department_code_unique_on_save(self):
        dept1 = Department.objects.create(name="Finance1")
        dept2 = Department.objects.create(name="Finance2")
        self.assertNotEqual(dept1.department_code, dept2.department_code)

User = get_user_model()
class EmployeeModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="hero@gmail.com", password = "12345678",username = "johnc1", first_name = "John", last_name = "Cena")
        self.dept = Department.objects.create(name = "Engineering")
        self.status = EmployeeStatus.objects.create(is_active = True)

    
    def test_create_employee_and_code_generation(self):
        emp = Employee.objects.create(
            user = self.user,
            role = Employee.EMPLOYEE,
            phone="9812345678",
            dob="1999-05-10",
            gender="M",
            department=self.dept,
            date_of_joining=timezone.now(),
            employee_status=self.status
        )
        self.assertIsNotNone(emp.employee_code)
        self.assertTrue(emp.employee_code.startswith("ENG"))
    
    def test_employee_str_representation(self):
        emp = Employee.objects.create(
            user = self.user,
            phone = "9812348778",
            date_of_joining = timezone.now()
        )
        self.assertEqual(str(emp), "John Cena")

    def test_employee_without_user_returns_fallback(self):
        emp = Employee.objects.create(
            phone = "9898981212",
            date_of_joining = timezone.now()
        )
        self.assertIn("Employee", str(emp))

    def test_employee_profile_creation(self):
        emp = Employee.objects.create(
            user = self.user,
            role = Employee.EMPLOYEE,
            phone="9812345671",
            dob="1999-05-11",
            gender="M",
            department=self.dept,
            date_of_joining=timezone.now(),
            employee_status=self.status
        )
        profile = EmployeeProfile.objects.create(employee = emp)
        self.assertEqual(str(profile), 'John Cena')


class LeaveModelTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(email = "leave@gmail.com", password = "leave1234", username = "alexbrown", first_name = "Alex", last_name = "Brown")
        dept = Department.objects.create(name = "QA")
        self.emp = Employee.objects.create(user=user, phone="9812345682", department=dept, date_of_joining=timezone.now())

    def test_valid_leave_creation(self):
        start = timezone.now().date() + timedelta(days=1)
        end = start + timedelta(days=2)
        leave = Leave.objects.create(employee=self.emp, start_date=start, end_date=end, leave_reason="Vacation")
        self.assertIn("Vacation", str(leave))

    def test_start_date_in_past_raises_error(self):
        start = timezone.now().date() - timedelta(days=1)
        with self.assertRaises(ValidationError):
            leave = Leave(employee=self.emp, start_date=start, end_date=start, leave_reason="Invalid")
            leave.clean()
    
class WorkingHourModelTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(email="work@mail.com", password="pass123",username ="Samlee", first_name="Sam", last_name="Lee")
        dept = Department.objects.create(name="Operations")
        self.emp = Employee.objects.create(user=user, phone="9812345683", department=dept, date_of_joining=timezone.now())

    def test_working_hour_creation(self):
        wh = WorkingHour.objects.create(employee=self.emp, day_of_week="monday", start_time="09:00", end_time="17:00")
        self.assertIn("monday", str(wh))


class EmployeeScheduleModelTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(email="schedule@mail.com", password="pass123", username="Nina123",first_name="Nina", last_name="Patel")
        dept = Department.objects.create(name="Marketing")
        self.emp = Employee.objects.create(user=user, phone="9812345684", department=dept, date_of_joining=timezone.now())
        self.schedule = EmployeeSchedule.objects.create(employee=self.emp)

    def test_default_availability(self):
        self.assertEqual(self.schedule.availability, "available")

    def test_update_availability_to_on_leave(self):
        today = timezone.now().date()
        Leave.objects.create(employee=self.emp, start_date=today, end_date=today + timedelta(days=2), leave_reason="Trip")
        self.schedule.update_availability()
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.availability, "on_leave")