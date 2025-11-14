# projects/tests/test_views.py
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from projects.models import Project
from employee.models import Employee, Department

User = get_user_model()


class ProjectViewSetTestCase(APITestCase):
    def setUp(self):
        self.department = Department.objects.create(name="IT")

        # Helper to create users + employees with required fields
        def create_employee(username, role, phone):
            user = User.objects.create_user(
                username=username,
                email=f"{username}@example.com",
                password="securepass123"
            )
            employee = Employee.objects.create(
                user=user,
                role=role,
                phone=phone,
                department=self.department,
                date_of_joining=timezone.now(),
                status=Employee.STATUS_ACTIVE,
                dob="1990-01-01",
                gender="M" if role != Employee.EMPLOYEE else "F",
                address="Kathmandu"
            )
            return user, employee

        self.user_hr, self.hr = create_employee("hr", Employee.HR, "9812345601")
        self.user_admin, self.admin = create_employee("admin", Employee.ADMIN, "9812345602")
        self.user_pm, self.pm = create_employee("pm", Employee.PROJECT_MANAGER, "9812345603")
        self.user_lead, self.lead = create_employee("lead", Employee.TEAM_LEAD, "9812345604")
        self.user_emp, self.emp = create_employee("emp", Employee.EMPLOYEE, "9812345605")
        self.user_no_profile = User.objects.create_user(
            username="noprof", email="noprof@example.com", password="securepass123"
        )

        # Create projects with end_date
        future = timezone.now() + timezone.timedelta(days=30)
        self.project1 = Project.objects.create(
            name="Project 1", manager=self.pm, team_lead=self.lead,
            department=self.department, end_date=future, created_by=self.admin
        )
        self.project2 = Project.objects.create(
            name="Project 2", manager=self.pm, department=self.department,
            end_date=future, created_by=self.admin
        )
        self.project3 = Project.objects.create(
            name="Project 3", department=self.department, end_date=future,
            created_by=self.admin
        )
        self.project2.members.add(self.emp)

        self.client = self.client  # APIClient is default

    def authenticate_user(self, user):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_hr_sees_all_projects(self):
        self.authenticate_user(self.user_hr)
        response = self.client.get(reverse("project-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)

    def test_admin_sees_all_projects(self):
        self.authenticate_user(self.user_admin)
        response = self.client.get(reverse("project-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)

    def test_pm_sees_managed_projects_only(self):
        self.authenticate_user(self.user_pm)
        response = self.client.get(reverse("project-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        project_ids = [p['id'] for p in response.data['results']]
        self.assertIn(self.project1.id, project_ids)
        self.assertIn(self.project2.id, project_ids)
        self.assertNotIn(self.project3.id, project_ids)

    def test_team_lead_sees_led_projects_only(self):
        self.authenticate_user(self.user_lead)
        response = self.client.get(reverse("project-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        project_ids = [p['id'] for p in response.data['results']]
        self.assertEqual(project_ids, [self.project1.id])

    def test_employee_sees_assigned_projects_only(self):
        self.authenticate_user(self.user_emp)
        response = self.client.get(reverse("project-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        project_ids = [p['id'] for p in response.data['results']]
        self.assertEqual(project_ids, [self.project2.id])

    def test_user_without_employee_profile_returns_empty_list(self):
        self.authenticate_user(self.user_no_profile)
        response = self.client.get(reverse("project-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'], [])