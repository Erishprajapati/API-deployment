from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.utils import timezone
from employee.models import *
from rest_framework_simplejwt.tokens import RefreshToken

class EmployeeAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="admin@mail.com", email="admin@mail.com", password="pass123")
        self.department = Department.objects.create(name="IT")
        self.status = EmployeeStatus.objects.create(is_active=True)
        self.employee = Employee.objects.create(
            user=self.user,
            phone="9812345670",
            department=self.department,
            date_of_joining=timezone.now(),
            employee_status=self.status
        )
        self.profile = EmployeeProfile.objects.create(employee=self.employee)

        # authenticate
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    # ----------------- EmployeeViewSet -----------------
    def test_employee_list(self):
        url = reverse("employee-list")  # ✅ correct
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.data) >= 1)

    def test_employee_create(self):
        url = reverse("employee-list")
        data = {
            "user": {"email": "new@mail.com", "full_name": "New User", "password": "pass12345"},
            "phone": "9812345678",
            "department": self.department.id,
            "dob": "1990-01-01",
            "gender": "M",
            "address": "Kathmandu",
            "date_of_joining": timezone.now(),
            "employee_status": self.status.id
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["employee"]["phone"], "9812345678")

    # ----------------- DepartmentViewSet -----------------
    def test_department_list(self):
        url = reverse("department-list")  # ✅ correct
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("IT", [d["name"] for d in response.data])

    # ----------------- EmployeeProfileViewSet -----------------
    def test_employee_profile_list_self(self):
        url = reverse("employeeprofile-list")  # ✅ corrected (no underscore)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["employee"], self.employee.id)

    # ----------------- LeaveViewSet -----------------
    def test_leave_create_valid(self):
        url = reverse("leave-list")  # ✅ correct
        data = {
            "employee": self.employee.id,
            "start_date": timezone.now().date() + timezone.timedelta(days=1),
            "end_date": timezone.now().date() + timezone.timedelta(days=2),
            "leave_reason": "Vacation"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["employee"], self.employee.id)

    # ----------------- WorkingHourViewSet -----------------
    def test_workinghour_create(self):
        url = reverse("workinghour-list")  # ✅ corrected (no underscore)
        data = {
            "employee": self.employee.id,
            "day_of_week": "monday",
            "start_time": "09:00:00",
            "end_time": "17:00:00"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)

    # ----------------- EmployeeScheduleViewSet -----------------
    def test_employee_schedule_list(self):
        schedule = EmployeeSchedule.objects.create(employee=self.employee, availability="available")
        url = reverse("employeeschedule-list")  # ✅ corrected (no underscore)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["employee"], self.employee.id)
