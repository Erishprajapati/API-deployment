# projects/tests/test_serializers.py
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from employee.models import Employee, Department
from projects.models import Project, ProjectDocuments, Tasks, TaskComment, Folder, List, FolderFile
from projects.serializers import (
    ProjectSerializer, ProjectDocumentSerializer, TaskSerializer,
    TaskCommentSerializer, FolderSerializer, FolderFileSerializer, ListSerializer
)
from django.contrib.auth import get_user_model
import os
from unittest.mock import patch

User = get_user_model()


@patch('projects.tasks.send_task_created_email.delay')
class ProjectSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="admin@example.com",
            username="admin@example.com",
            password="pass123456"
        )
        self.department = Department.objects.create(name="IT")
        self.employee = Employee.objects.create(
            user=self.user,
            phone="9812345670",
            department=self.department,
            date_of_joining=timezone.now(),
            status=Employee.STATUS_ACTIVE,
            role=Employee.ADMIN,
            dob="1990-01-01",
            gender="M",
            address="Kathmandu"
        )
        self.project = Project.objects.create(
            name="ERP",
            department=self.department,
            created_by=self.employee,
            manager=self.employee,
            team_lead=self.employee
        )

    def test_project_serializer_output(self, mock_send_email):
        serializer = ProjectSerializer(instance=self.project)
        data = serializer.data
        self.assertEqual(data['name'], "ERP")
        self.assertEqual(data['department'], self.department.id)
        self.assertEqual(data['manager_details']['id'], self.employee.id)
        self.assertEqual(data['team_lead_details']['id'], self.employee.id)
        self.assertEqual(data['documents'], [])

    def test_project_serializer_create_validation(self, mock_send_email):
        future_date = (timezone.now() + timezone.timedelta(days=30)).isoformat()
        input_data = {
            "name": "New Project",
            "department": self.department.id,
            "manager": self.employee.id,
            "team_lead": self.employee.id,
            "end_date": future_date
        }
        serializer = ProjectSerializer(data=input_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        project = serializer.save(created_by=self.employee)
        self.assertEqual(project.name, "New Project")
        self.assertEqual(project.manager.id, self.employee.id)

    def test_project_document_serializer(self, mock_send_email):
        file = SimpleUploadedFile("contract.txt", b"Contract content")
        doc = ProjectDocuments.objects.create(
            project=self.project,
            file=file,
            description="Contract"
        )
        serializer = ProjectDocumentSerializer(instance=doc)
        data = serializer.data
        self.assertEqual(data['description'], "Contract")
        filename = os.path.basename(doc.file.name)
        self.assertTrue(filename.startswith("contract"))  

    def test_task_serializer_validation(self, mock_send_email):
        mock_request = type('MockRequest', (), {})()
        mock_request.user = self.user
        mock_request.user.employee_profile = self.employee

        input_data = {
            "project": self.project.id,
            "title": "Setup DB",
            "assigned_to_id": self.employee.id,
            "due_date": (timezone.now() + timezone.timedelta(days=5)).isoformat()
        }
        serializer = TaskSerializer(data=input_data, context={'request': mock_request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        task = serializer.save()
        self.assertEqual(task.title, "Setup DB")
        self.assertEqual(task.created_by, self.employee)

    def test_task_serializer_duplicate_title(self, mock_send_email):
        Tasks.objects.create(
            project=self.project,
            title="Duplicate Task",
            created_by=self.employee
        )
        input_data = {
            "project": self.project.id,
            "title": "duplicate task",
            "assigned_to_id": self.employee.id,
            "due_date": (timezone.now() + timezone.timedelta(days=5)).isoformat()
        }
        serializer = TaskSerializer(data=input_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("title", serializer.errors)

    def test_task_comment_serializer(self, mock_send_email):
        task = Tasks.objects.create(project=self.project, title="Task 1", created_by=self.employee)
        comment = TaskComment.objects.create(
            task=task,
            author=self.employee,
            commented_by=self.employee,
            description="Nice work!"
        )
        serializer = TaskCommentSerializer(instance=comment)
        self.assertEqual(serializer.data['description'], "Nice work!")
        self.assertEqual(serializer.data['author'], self.employee.user.username)
        self.assertEqual(serializer.data['commented_by'], self.employee.user.username)

    def test_folder_serializer_read_only_fields(self, mock_send_email):
        folder = Folder.objects.create(
            project=self.project,
            title="Root",
            description="Main",
            created_by=self.employee
        )
        serializer = FolderSerializer(instance=folder)
        self.assertEqual(serializer.data['path'], folder.path)
        self.assertIn('child_count', serializer.data)
        self.assertIn('lists_count', serializer.data)

    def test_folder_file_serializer(self, mock_send_email):
        folder = Folder.objects.create(
            project=self.project,
            title="Docs",
            description="Docs Folder",
            created_by=self.employee
        )
        file = SimpleUploadedFile("design.pdf", b"PDF data")
        ffile = FolderFile.objects.create(folder=folder, uploaded_by=self.employee, file=file)
        serializer = FolderFileSerializer(instance=ffile)
        self.assertEqual(serializer.data['folder'], folder.id)
        self.assertGreater(ffile.size_bytes, 0)

    def test_list_serializer(self, mock_send_email):
        folder = Folder.objects.create(
            project=self.project,
            title="Docs",
            description="Docs Folder",
            created_by=self.employee
        )
        lst = List.objects.create(project=self.project, folder=folder, name="Sprint 1")
        serializer = ListSerializer(instance=lst)
        self.assertEqual(serializer.data['name'], "Sprint 1")
        self.assertEqual(serializer.data['folder'], folder.id)