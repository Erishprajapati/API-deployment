# employee/tests/test_serializers.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from employee.models import Department, Employee
from employee.serializers import UserSerializer, EmployeeSerializer

User = get_user_model()


class UserSerializerTest(TestCase):
    def test_user_serializer_create(self):
        data = {
            "email": "erish@gmail.com",
            "first_name": "Erish",
            "last_name": "Prajapati",
            "password": "123456789"
        }
        serializer = UserSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.email, "erish@gmail.com")
        self.assertEqual(user.username, "erish@gmail.com")
        self.assertEqual(user.first_name, "Erish")
        self.assertEqual(user.last_name, "Prajapati")
        self.assertTrue(user.check_password("123456789"))
        self.assertEqual(user.get_full_name(), "Erish Prajapati")

    def test_user_serializer_missing_password(self):
        data = {"email": "suman@example.com", "first_name": "Suman"}
        serializer = UserSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_user_serializer_invalid_email(self):
        data = {"email": "not-an-email", "first_name": "Test", "password": "12345678"}
        serializer = UserSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)


class EmployeeSerializerTest(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="HR")

    def test_employee_serializer_create_success(self):
        user_data = {
            "email": "sumanthapa@gmail.com",
            "first_name": "Suman",
            "last_name": "thapa",
            "password": "pass12345"
        }
        emp_data = {
            "user": user_data,
            "phone": "9812345678",
            "department": self.department.id,
            "dob": "1995-05-15",
            "gender": "M",
            "address": "Pokhara",
            "date_of_joining": timezone.now().isoformat(),
            "status": "active",
            "role": Employee.EMPLOYEE
        }
        serializer = EmployeeSerializer(data=emp_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        employee = serializer.save()
        self.assertEqual(employee.user.email, "sumanthapa@gmail.com")
        self.assertEqual(employee.department, self.department)
        self.assertEqual(employee.phone, "9812345678")
        self.assertIsNotNone(employee.employee_code)

    def test_employee_serializer_duplicate_phone(self):
        # Create first employee
        user1 = User.objects.create_user(
            username="first@example.com",
            email="first@example.com",
            password="securepass123"
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
            "password": "anotherpass123"
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

    # def test_employee_serializer_duplicate_name_in_same_department(self):
    #     # Create first employee
    #     user1 = User.objects.create_user(
    #         username="alice1@example.com",
    #         email="alice1@example.com",
    #         password="securepass123"
    #     )
    #     Employee.objects.create(
    #         user=user1,
    #         phone="9812345601",
    #         department=self.department,
    #         date_of_joining=timezone.now(),
    #         status=Employee.STATUS_ACTIVE
    #     )

    #     # Try duplicate name in same dept
    #     user_data = {
    #         "email": "alice2@example.com",
    #         "first_name": "Alice",
    #         "last_name": "Smith",
    #         "password": "anotherpass123"
    #     }
    #     emp_data = {
    #         "user": user_data,
    #         "phone": "9812345602",
    #         "department": self.department.id,
    #         "dob": "1990-01-01",
    #         "gender": "F",
    #         "address": "KTM",
    #         "date_of_joining": timezone.now().isoformat(),
    #     }
    #     serializer = EmployeeSerializer(data=emp_data)
    #     self.assertFalse(serializer.is_valid())
    #     self.assertIn("name", serializer.errors)
    def test_employee_serializer_duplicate_name_in_same_department(self):
        user1 = User.objects.create_user(
            username="alice1@example.com",
            email="alice1@example.com",
            first_name="Alice", 
            last_name="Smith",    
            password="securepass123"
        )
        Employee.objects.create(
            user=user1,
            phone="9812345601",
            department=self.department,
            date_of_joining=timezone.now(),
            status=Employee.STATUS_ACTIVE
        )

        user_data = {
            "email": "alice2@example.com",
            "first_name": "alice",
            "last_name": "SMITH",    
            "password": "anotherpass123"
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
        self.assertFalse(serializer.is_valid(), serializer.errors)
        self.assertIn("name", serializer.errors)
        self.assertIn("already exists in this department", str(serializer.errors["name"]))

    def test_employee_serializer_unique_name_allowed_in_different_department(self):
        dept2 = Department.objects.create(name="Finance")
        user1 = User.objects.create_user(
            username="alice_hr@example.com",
            email="alice_hr@example.com",
            password="securepass123"
        )
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
            "password": "anotherpass123"
        }
        emp_data = {
            "user": user_data,
            "phone": "9812345611",
            "department": dept2.id,
            "dob": "1990-01-01",
            "gender": "F",
            "address": "KTM",
            "date_of_joining": timezone.now().isoformat(),
        }
        serializer = EmployeeSerializer(data=emp_data)
        self.assertTrue(serializer.is_valid())

    def test_employee_serializer_invalid_nepali_phone(self):
        user_data = {
            "email": "test@x.com",
            "first_name": "X",
            "last_name": "Y",
            "password": "12345678"
        }
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