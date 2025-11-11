# employee/tests/test_serializers.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from employee.models import Department, Employee
from employee.serializers import UserSerializer, EmployeeSerializer

User = get_user_model()

class UserSerializerTest(TestCase):
    def test_user_serializer_create(self):
        data = {
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "password": "securepassword123"
        }
        serializer = UserSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.email, "john@example.com")
        self.assertEqual(user.username, "john@example.com") 
        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")
        self.assertTrue(user.check_password("securepassword123"))
        self.assertEqual(user.get_full_name(), "John Doe")

    def test_user_serializer_missing_password(self):
        data = {"email": "test@example.com", "first_name": "Test"}
        serializer = UserSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_user_serializer_invalid_email(self):
        data = {"email": "not-an-email", "first_name": "Test", "password": "123"}
        serializer = UserSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)


class EmployeeSerializerTest(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="HR")

    def test_employee_serializer_create_success(self):
        user_data = {
            "email": "alice@example.com",
            "first_name": "Alice",
            "last_name": "Smith",
            "password": "pass12345"
        }
        emp_data = {
            "user": user_data,
            "phone": "9812345678",
            "department": self.department.id,
            "dob": "1990-01-01",
            "gender": "F",
            "address": "Kathmandu",
            "date_of_joining": timezone.now().isoformat(),
            # ❌ DO NOT include 'status' or 'employee_status' — it's default or read-only
        }
        serializer = EmployeeSerializer(data=emp_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        employee = serializer.save()
        self.assertEqual(employee.user.email, "alice@example.com")
        self.assertEqual(employee.department, self.department)
        self.assertEqual(employee.phone, "9812345678")
        self.assertIsNotNone(employee.employee_code)

    def test_employee_serializer_duplicate_phone(self):
        # Create first employee
        user1 = User.objects.create_user(
            email="first@example.com",
            username="first@example.com",
            password="pass123"
        )
        Employee.objects.create(
            user=user1,
            phone="9812345678",
            department=self.department,
            date_of_joining=timezone.now(),
            status=Employee.STATUS_ACTIVE
        )

        # Try to create second with same phone
        user_data = {
            "email": "second@example.com",
            "first_name": "Bob",
            "last_name": "Brown",
            "password": "pass12345"
        }
        emp_data = {
            "user": user_data,
            "phone": "9812345678",  # duplicate
            "department": self.department.id,
            "dob": "1992-05-10",
            "gender": "M",
            "address": "Pokhara",
            "date_of_joining": timezone.now().isoformat(),
        }
        serializer = EmployeeSerializer(data=emp_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("phone", serializer.errors)
        self.assertIn("already registered", str(serializer.errors["phone"]))

    def test_employee_serializer_duplicate_name_in_same_department(self):
        # Create first employee
        user1 = User.objects.create_user(email="alice1@example.com", password="pass")
        Employee.objects.create(
            user=user1,
            phone="9812345601",
            department=self.department,
            date_of_joining=timezone.now(),
            status=Employee.STATUS_ACTIVE
        )

        # Try duplicate name in same dept
        user_data = {
            "email": "alice2@example.com",
            "first_name": "Alice",   # same first
            "last_name": "Smith",    # same last
            "password": "pass123"
        }
        emp_data = {
            "user": user_data,
            "phone": "9812345602",
            "department": self.department.id,
            "dob": "1990-01-01",
            "gender": "F",
            "address": "KTM",
            "date_of_joining": timezone.now().isoformat(),
        }
        serializer = EmployeeSerializer(data=emp_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_employee_serializer_unique_name_allowed_in_different_department(self):
        dept2 = Department.objects.create(name="Finance")
        # Alice in HR
        user1 = User.objects.create_user(email="alice_hr@example.com", password="pass")
        Employee.objects.create(
            user=user1,
            phone="9812345610",
            department=self.department,  # HR
            date_of_joining=timezone.now(),
            status=Employee.STATUS_ACTIVE
        )

        # Alice in Finance → should be allowed
        user_data = {
            "email": "alice_fin@example.com",
            "first_name": "Alice",
            "last_name": "Smith",
            "password": "pass123"
        }
        emp_data = {
            "user": user_data,
            "phone": "9812345611",
            "department": dept2.id,  # Different dept
            "dob": "1990-01-01",
            "gender": "F",
            "address": "KTM",
            "date_of_joining": timezone.now().isoformat(),
        }
        serializer = EmployeeSerializer(data=emp_data)
        self.assertTrue(serializer.is_valid())

    def test_employee_serializer_invalid_nepali_phone(self):
        user_data = {"email": "test@x.com", "first_name": "X", "last_name": "Y", "password": "12345678"}
        emp_data = {
            "user": user_data,
            "phone": "9512345678",  # starts with 95 → invalid
            "department": self.department.id,
            "dob": "1990-01-01",
            "gender": "M",
            "address": "KTM",
            "date_of_joining": timezone.now().isoformat(),
        }
        serializer = EmployeeSerializer(data=emp_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("phone", serializer.errors)