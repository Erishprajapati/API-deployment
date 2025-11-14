# employee/tests/test_api.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.utils import timezone
from employee.models import Department, Employee, EmployeeProfile, Leave, EmployeeSchedule
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class EmployeeAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create admin user
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            username="admin@example.com",
            password="adminpass123",
            first_name="Admin",
            last_name="User"
        )
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()

        # Create department
        self.department = Department.objects.create(name="IT")
        self.employee = Employee.objects.create(
            user=self.admin_user,
            phone="9812345670",
            department=self.department,
            date_of_joining=timezone.now(),
            status=Employee.STATUS_ACTIVE,
            role=Employee.ADMIN,
            dob="1990-01-01",
            gender="M",
            address="Kathmandu"
        )

        # Create profile
        # self.profile = EmployeeProfile.objects.create(employee=self.employee)

        # Authenticate client
        refresh = RefreshToken.for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_department_list(self):
        url = reverse("employee:department-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Handle paginated response
        results = response.data.get('results', response.data)  # fallback if pagination off
        self.assertTrue(any(d['name'] == 'IT' for d in results))

    def test_department_create(self):
        url = reverse("employee:department-list")
        data = {
            "name": "HR",
            "description": "Human Resources",
            "working_start_time": "08:00",
            "working_end_time": "16:00"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "HR")

    def test_employee_list(self):
        url = reverse("employee:employee-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)

    def test_employee_create(self):
        url = reverse("employee:employee-list")
        data = {
            "user": {
                "email": "newuser@example.com",
                "first_name": "New",
                "last_name": "User",
                "password": "strongpass123"
            },
            "phone": "9812345678",
            "department": self.department.id,
            "dob": "1995-05-15",
            "gender": "M",
            "address": "Pokhara",
            "date_of_joining": timezone.now().isoformat(),
            "status": "active",
            "role": Employee.EMPLOYEE
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["employee"]["phone"], "9812345678")
        self.assertTrue("employee_code" in response.data["employee"])

    def test_employee_create_duplicate_phone(self):
        url = reverse("employee:employee-list")
        data1 = {
            "user": {"email": "u1@example.com", "first_name": "U1", "last_name": "Test", "password": "pass12345"},  # 9 chars ✅
            "phone": "9812345671",
            "department": self.department.id,
            "dob": "1990-01-01",
            "gender": "M",
            "address": "KTM",
            "date_of_joining": timezone.now().isoformat(),
            "status": "active"
        }
        self.client.post(url, data1, format="json")

        data2 = {**data1, "user": {**data1["user"], "email": "u2@example.com"}}
        response = self.client.post(url, data2, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("phone", response.data)  # Now phone error should appear

    def test_leave_create_valid(self):
        url = reverse("employee:leave-list")
        tomorrow = timezone.now().date() + timezone.timedelta(days=1)
        next_day = tomorrow + timezone.timedelta(days=1)
        data = {
            "start_date": tomorrow.isoformat(),
            "end_date": next_day.isoformat(),
            "leave_reason": "Family event"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["employee_name"], "Admin User")

    def test_leave_create_past_date(self):
        url = reverse("employee:leave-list")
        yesterday = timezone.now().date() - timezone.timedelta(days=1)
        tomorrow = timezone.now().date() + timezone.timedelta(days=1)
        data = {
            "start_date": yesterday.isoformat(),
            "end_date": tomorrow.isoformat(),
            "leave_reason": "Invalid"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("start_date", str(response.data))

    def test_employee_schedule_list(self):
        EmployeeSchedule.objects.create(employee=self.employee, availability="available")
        url = reverse("employee:employee-schedule-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        results = response.data.get('results', response.data)
        self.assertEqual(results[0]["employee"], self.employee.id)

    def test_department_working_hours(self):
        url = reverse("employee:department-working-hours-list")  # Adjust name if needed
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    def test_employee_profile_list_self(self):
    # Ensure only one profile exists
        EmployeeProfile.objects.filter(employee=self.employee).delete()
        EmployeeProfile.objects.create(employee=self.employee)

        url = reverse("employee:employee-profile-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        results = response.data.get('results', response.data)
        self.assertEqual(results[0]["employee"], self.employee.id)