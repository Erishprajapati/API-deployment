from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from projects.models import Project, Employee, Department
from django.contrib.auth.models import User

class ProjectViewSetTest(APITestCase):

    def setUp(self):
        # Create department
        self.department = Department.objects.create(name="IT Department")

        # Create users
        self.pm_user = User.objects.create_user(username='pm', password='pm123')
        self.employee_user = User.objects.create_user(username='emp', password='emp123')

        # Create Employee profiles linked to department
        self.pm_employee = Employee.objects.create(
            user=self.pm_user,
            role=Employee.PROJECT_MANAGER,
            department=self.department
        )
        self.emp_employee = Employee.objects.create(
            user=self.employee_user,
            role=Employee.EMPLOYEE,
            department=self.department
        )

        # API URL for Project list
        self.project_url = reverse('project-list')

    def test_create_project_as_pm(self):
        """Project Manager should automatically become manager of project."""
        self.client.login(username='pm', password='pm123')
        data = {
            "name": "New Project",
            "description": "Test project",
            "department": self.department.id
        }
        response = self.client.post(self.project_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        project = Project.objects.first()
        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(project.manager, self.pm_employee)
        self.assertEqual(project.department, self.department)

    def test_create_project_as_non_pm(self):
        """Non-PM employee should not be assigned as manager."""
        self.client.login(username='emp', password='emp123')
        data = {
            "name": "Employee Project",
            "description": "Test project by employee",
            "department": self.department.id
        }
        response = self.client.post(self.project_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        project = Project.objects.first()
        self.assertEqual(Project.objects.count(), 1)
        # Manager should not be assigned for non-PM
        self.assertIsNone(project.manager)
        self.assertEqual(project.department, self.department)

    def test_create_project_missing_required_field(self):
        """Should return 400 if required fields are missing."""
        self.client.login(username='pm', password='pm123')
        data = {
            # "name" is missing
            "description": "Missing name field",
            "department": self.department.id
        }
        response = self.client.post(self.project_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)
        self.assertEqual(Project.objects.count(), 0)