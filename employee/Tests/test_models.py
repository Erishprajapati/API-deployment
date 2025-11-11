# employee/tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from employee.models import Department, Employee, Leave, WorkingHour, EmployeeSchedule
from django.core.exceptions import ValidationError
from datetime import timedelta
from unittest.mock import patch

User = get_user_model()

class DepartmentModelTest(TestCase):
    def test_create_department_generates_code(self):
        dept = Department.objects.create(name="Development Team")
        self.assertTrue(dept.department_code.startswith("DEV"))
        self.assertEqual(str(dept), "Development Team")

    def test_department_code_unique_on_save(self):
        dept1 = Department.objects.create(name="Finance1")
        dept2 = Department.objects.create(name="Finance2")
        self.assertNotEqual(dept1.department_code, dept2.department_code)

    def test_clean_rejects_equal_start_end_time(self):
        dept = Department(name="Test", working_start_time="09:00", working_end_time="09:00")
        with self.assertRaises(ValidationError) as cm:
            dept.full_clean()
        self.assertIn("must be different", str(cm.exception))

    def test_clean_rejects_shift_longer_than_8_hours(self):
        dept = Department(name="LongShift", working_start_time="08:00", working_end_time="18:00")  # 10 hours
        with self.assertRaises(ValidationError) as cm:
            dept.full_clean()
        self.assertIn("exceeds the maximum allowed", str(cm.exception))

    @patch('employee.models.timezone')
    def test_is_on_shift_handles_overnight_shift(self, mock_tz):
        dept = Department.objects.create(
            name="NightShift",
            working_start_time="22:00",
            working_end_time="06:00"
        )
        # Mock current time to 2 AM
        mock_now = timezone.datetime(2025, 1, 1, 2, 0, tzinfo=timezone.get_current_timezone())
        mock_tz.now.return_value = mock_now
        mock_tz.localtime.return_value = timezone.localtime(mock_now)

        self.assertTrue(dept.is_on_shift())


class EmployeeModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="hero@gmail.com",
            password="12345678",
            username="johnc1",
            first_name="John",
            last_name="Cena"
        )
        self.dept = Department.objects.create(name="Engineering")

    def test_create_employee_and_code_generation(self):
        now = timezone.now()
        emp = Employee.objects.create(
            user=self.user,
            role=Employee.EMPLOYEE,
            phone="9812345678",
            dob="1999-05-10",
            gender="M",
            department=self.dept,
            date_of_joining=now,
            status=Employee.STATUS_ACTIVE
        )
        self.assertIsNotNone(emp.employee_code)
        self.assertTrue(emp.employee_code.startswith("ENG"))
        self.assertIn(now.strftime("%Y%m"), emp.employee_code)

    def test_employee_str_representation(self):
        emp = Employee.objects.create(
            user=self.user,
            phone="9812348778",
            date_of_joining=timezone.now(),
            status=Employee.STATUS_ACTIVE
        )
        self.assertEqual(str(emp), "John Cena")

    def test_employee_without_user_returns_fallback(self):
        emp = Employee.objects.create(
            phone="9898981212",
            date_of_joining=timezone.now(),
            status=Employee.STATUS_ACTIVE
        )
        self.assertTrue(str(emp).startswith("Employee"))

    def test_employee_inherits_department_working_hours(self):
        dept = Department.objects.create(
            name="Support",
            working_start_time="08:00",
            working_end_time="16:00"
        )
        emp = Employee.objects.create(
            phone="9812345699",
            department=dept,
            date_of_joining=timezone.now(),
            status=Employee.STATUS_ACTIVE
        )
        self.assertEqual(emp.working_start_time, dept.working_start_time)
        self.assertEqual(emp.working_end_time, dept.working_end_time)

    def test_employee_code_generation_handles_monthly_reset(self):
        now = timezone.now()
        dept = Department.objects.create(name="TestDept")

        # First employee in month
        emp1 = Employee.objects.create(
            phone="9812345601",
            department=dept,
            date_of_joining=now,
            status=Employee.STATUS_ACTIVE
        )
        # Second
        emp2 = Employee.objects.create(
            phone="9812345602",
            department=dept,
            date_of_joining=now,
            status=Employee.STATUS_ACTIVE
        )

        self.assertIn("-001", emp1.employee_code)
        self.assertIn("-002", emp2.employee_code)


class LeaveModelTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(
            email="leave@gmail.com",
            password="leave1234",
            username="alexbrown",
            first_name="Alex",
            last_name="Brown"
        )
        dept = Department.objects.create(name="QA")
        self.emp = Employee.objects.create(
            user=user,
            phone="9812345682",
            department=dept,
            date_of_joining=timezone.now(),
            status=Employee.STATUS_ACTIVE
        )

    def test_valid_leave_creation(self):
        start = timezone.now().date() + timedelta(days=1)
        end = start + timedelta(days=2)
        leave = Leave.objects.create(
            employee=self.emp,
            start_date=start,
            end_date=end,
            leave_reason="Vacation"
        )
        self.assertIn("Vacation", str(leave))
        self.assertEqual(leave.total_days, 3)

    def test_start_date_in_past_raises_error(self):
        start = timezone.now().date() - timedelta(days=1)
        leave = Leave(
            employee=self.emp,
            start_date=start,
            end_date=start,
            leave_reason="Invalid"
        )
        with self.assertRaises(ValidationError) as cm:
            leave.clean()
        self.assertIn("cannot be in the past", str(cm.exception))

    def test_end_date_before_start_date_raises_error(self):
        today = timezone.now().date()
        leave = Leave(
            employee=self.emp,
            start_date=today + timedelta(days=2),
            end_date=today + timedelta(days=1),
            leave_reason="Invalid"
        )
        with self.assertRaises(ValidationError) as cm:
            leave.clean()
        self.assertIn("cannot be before start date", str(cm.exception))


class WorkingHourModelTest(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="Operations")

    def test_working_hour_creation(self):
        wh = WorkingHour.objects.create(
            department=self.dept,
            days_of_week=['monday', 'tuesday'],
            start_time="09:00",
            end_time="17:00"
        )
        self.assertIn("monday", wh.days_of_week)
        self.assertIn("Operations", str(wh))


class EmployeeScheduleModelTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(
            email="schedule@mail.com",
            password="pass123",
            username="Nina123",
            first_name="Nina",
            last_name="Patel"
        )
        dept = Department.objects.create(
            name="Marketing",
            working_start_time="09:00",
            working_end_time="17:00"
        )
        self.emp = Employee.objects.create(
            user=user,
            phone="9812345684",
            department=dept,
            date_of_joining=timezone.now(),
            status=Employee.STATUS_ACTIVE
        )
        self.schedule = EmployeeSchedule.objects.create(employee=self.emp)

    @patch('employee.models.timezone')
    def test_update_availability_during_working_hours(self, mock_tz):
        # Mock current time to 10:00 AM
        mock_now = timezone.datetime(2025, 1, 1, 10, 0, tzinfo=timezone.get_current_timezone())
        mock_tz.now.return_value = mock_now
        mock_tz.localtime.return_value = timezone.localtime(mock_now)

        self.schedule.update_availability()
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.availability, "available")

    @patch('employee.models.timezone')
    def test_update_availability_outside_working_hours(self, mock_tz):
        # Mock current time to 8:00 PM
        mock_now = timezone.datetime(2025, 1, 1, 20, 0, tzinfo=timezone.get_current_timezone())
        mock_tz.now.return_value = mock_now
        mock_tz.localtime.return_value = timezone.localtime(mock_now)

        self.schedule.update_availability()
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.availability, "off_shift")

    @patch('employee.models.timezone')
    def test_update_availability_to_on_leave(self, mock_tz):
        today = timezone.now().date()
        mock_now = timezone.datetime.combine(today, timezone.datetime.min.time().replace(hour=12))
        mock_now = mock_now.replace(tzinfo=timezone.get_current_timezone())
        mock_tz.now.return_value = mock_now
        mock_tz.localtime.return_value = timezone.localtime(mock_now)
        Leave.objects.create(
            employee=self.emp,
            start_date=today,
            end_date=today + timedelta(days=2),
            leave_reason="Trip",
            status="APPROVED"
        )

        self.schedule.update_availability()
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.availability, "on_leave")