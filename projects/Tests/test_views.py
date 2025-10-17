from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from django.contrib.auth.models import User
from projects.models import Project
from employee.models import Employee, Department
from datetime import date

class ProjectViewSetTestCase(APITestCase):
    def setUp(self):
        # Create department
        self.department = Department.objects.create(name="IT")

        # Create users
        self.user_hr = User.objects.create_user(username="hr", password="pass")
        self.user_admin = User.objects.create_user(username="admin", password="pass")
        self.user_pm = User.objects.create_user(username="pm", password="pass")
        self.user_lead = User.objects.create_user(username="lead", password="pass")
        self.user_emp = User.objects.create_user(username="emp", password="pass")
        self.user_no_profile = User.objects.create_user(username="noprof", password="pass")

        # Create employee profiles
        self.hr = Employee.objects.create(user=self.user_hr, role=Employee.HR, date_of_joining=date.today())
        self.admin = Employee.objects.create(user=self.user_admin, role=Employee.ADMIN, date_of_joining=date.today(), phone="9826765644")
        self.pm = Employee.objects.create(user=self.user_pm, role=Employee.PROJECT_MANAGER, date_of_joining=date.today(), phone="9826765641")
        self.lead = Employee.objects.create(user=self.user_lead, role=Employee.TEAM_LEAD, date_of_joining=date.today(), phone="9826765614")
        self.emp = Employee.objects.create(user=self.user_emp, role=Employee.EMPLOYEE, date_of_joining=date.today(), phone="9826761644")

        # Create projects
        self.project1 = Project.objects.create(name="Project 1", manager=self.pm, team_lead=self.lead, department=self.department)
        self.project2 = Project.objects.create(name="Project 2", manager=self.pm, department=self.department)
        self.project3 = Project.objects.create(name="Project 3", department=self.department)  # not assigned

        # Add members correctly
        self.project2.members.add(self.emp)

        # DRF API client
        self.client = APIClient()
        self.url = reverse("project-list")

    # --- Tests ---
    def test_hr_sees_all_projects(self):
        self.client.force_authenticate(user=self.user_hr)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), Project.objects.count())

    def test_admin_sees_all_projects(self):
        self.client.force_authenticate(user=self.user_admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), Project.objects.count())

    def test_pm_sees_managed_projects_only(self):
        self.client.force_authenticate(user=self.user_pm)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertTrue(all(proj['id'] in [self.project1.id, self.project2.id] for proj in results))

    def test_team_lead_sees_led_projects_only(self):
        self.client.force_authenticate(user=self.user_lead)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertTrue(all(proj['id'] in [self.project1.id] for proj in results))

    def test_employee_sees_assigned_projects_only(self):
        self.client.force_authenticate(user=self.user_emp)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertTrue(all(proj['id'] in [self.project2.id] for proj in results))

    def test_user_without_employee_profile_returns_empty_list(self):
        self.client.force_authenticate(user=self.user_no_profile)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'], [])
