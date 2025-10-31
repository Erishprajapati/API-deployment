# from django.utils import timezone
# from django.test import TestCase
# from rest_framework.exceptions import ValidationError
# from employee.models import * 
# from employee.serializers import *


# class UserSerializer(TestCase):
    

# class UserSerializerTest(TestCase):
#     def test_user_serializer_create(self):
#         data = {"email": "john@mail.com", "full_name": "John Doe", "password": "password123"}
#         serializer = UserSerializer(data=data)
#         self.assertTrue(serializer.is_valid(), serializer.errors)
#         user = serializer.save()
#         self.assertEqual(user.first_name, "John")
#         self.assertEqual(user.last_name, "Doe")
#         self.assertTrue(user.check_password("password123"))


# class EmployeeSerializerTest(TestCase):
#     def setUp(self):
#         self.department = Department.objects.create(name="HR")
#         self.status = EmployeeStatus.objects.create(is_active=True)

#     def test_employee_serializer_create(self):
#         user_data = {"email": "alice@mail.com", "full_name": "Alice Smith", "password": "pass12345"}
#         emp_data = {
#             "user": user_data,
#             "phone": "9812345678",
#             "department": self.department.id,
#             "dob": "1990-01-01",
#             "gender": "F",
#             "address": "Kathmandu",
#             "date_of_joining": timezone.now(),
#             "employee_status": self.status.id,
#         }
#         serializer = EmployeeSerializer(data=emp_data)
#         self.assertTrue(serializer.is_valid(), serializer.errors)
#         emp = serializer.save()
#         self.assertEqual(emp.user.email, "alice@mail.com")
#         self.assertEqual(emp.department, self.department)

#     def test_employee_serializer_duplicate_phone(self):
#         # create existing employee
#         Employee.objects.create(
#             user=User.objects.create_user(username="existing@mail.com", email="existing@mail.com", password="pass123"),
#             phone="9812345678",
#             department=self.department,
#             date_of_joining=timezone.now(),
#             employee_status=self.status
#         )
#         user_data = {"email": "bob@mail.com", "full_name": "Bob Brown", "password": "pass12345"}
#         emp_data = {
#             "user": user_data,
#             "phone": "9812345678",  # duplicate
#             "department": self.department.id,
#             "dob": "1990-01-01",
#             "gender": "M",
#             "address": "Kathmandu",
#             "date_of_joining": timezone.now(),
#             "employee_status": self.status.id,
#         }
#         serializer = EmployeeSerializer(data=emp_data)
#         with self.assertRaises(ValidationError):
#             serializer.is_valid(raise_exception=True) 

"""this testcase are passed"""