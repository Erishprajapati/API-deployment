from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from employee.models import Employee, EmployeeStatus, Department, User
from projects.models import Project, ProjectDocuments, Tasks, TaskComment, Folder, List, FolderFile
from projects.serializers import *
import os
class ProjectSerializerTests(TestCase):
    def setUp(self):
        # create employee and related objects
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
        # create a project
        self.project = Project.objects.create(
            name="ERP", department=self.department, created_by=self.employee,
            manager=self.employee, team_lead=self.employee
        )

    # ---------------- Project Serializer ----------------
    def test_project_serializer_output(self):
        serializer = ProjectSerializer(instance=self.project)
        data = serializer.data
        self.assertEqual(data['name'], "ERP")
        self.assertEqual(data['department'], self.department.id)
        self.assertEqual(data['manager']['id'], self.employee.id)
        self.assertEqual(data['team_lead']['id'], self.employee.id)
        self.assertEqual(data['documents'], [])

    def test_project_serializer_create_validation(self):
        input_data = {
            "name": "New Project",
            "department": self.department.id,
            "manager_ids": self.employee.id,
            "team_lead_ids": self.employee.id
        }
        serializer = ProjectSerializer(data=input_data)
        self.assertTrue(serializer.is_valid())
        project = serializer.save()
        self.assertEqual(project.name, "New Project")
        self.assertEqual(project.manager.id, self.employee.id)

    # ---------------- ProjectDocument Serializer ----------------
    # def test_project_document_serializer(self):
    #     file = SimpleUploadedFile("contract.txt", b"Contract content")
    #     doc = ProjectDocuments.objects.create(project=self.project, file=file, description="Contract")
    #     serializer = ProjectDocumentSerializer(instance=doc)
    #     data = serializer.data
    #     self.assertEqual(data['description'], "Contract")
    #     # self.assertIn("contract.txt", str(data['file']))
    #     self.assertTrue("contract.txt" in doc.file.name)

    def test_project_document_serializer(self):
        file = SimpleUploadedFile("contract.txt", b"Contract content")
        doc = ProjectDocuments.objects.create(project=self.project, file=file, description="Contract")
        serializer = ProjectDocumentSerializer(instance=doc)
        data = serializer.data
        self.assertEqual(data['description'], "Contract")
        
        # Get the base filename only
        filename = os.path.basename(doc.file.name)
        self.assertIn("contract.txt", filename)

    # ---------------- Tasks Serializer ----------------
    def test_task_serializer_validation(self):
        input_data = {
            "project": self.project.id,
            "title": "Setup DB",
            "assigned_to": self.employee.id
        }
        serializer = TaskSerializer(data=input_data)
        # assign created_by manually if needed in context
        serializer.context['request'] = type('Request', (), {'user': self.user})()
        self.assertTrue(serializer.is_valid())
        task = serializer.save(created_by=self.employee)
        self.assertEqual(task.title, "Setup DB")

    def test_task_serializer_duplicate_title(self):
        Tasks.objects.create(project=self.project, title="Duplicate Task", created_by=self.employee)
        serializer = TaskSerializer(data={
            "project": self.project.id,
            "title": "Duplicate Task",
            "assigned_to": self.employee.id
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("title", serializer.errors)

    # ---------------- TaskComment Serializer ----------------
    def test_task_comment_serializer(self):
        task = Tasks.objects.create(project=self.project, title="Task 1", created_by=self.employee)
        comment = TaskComment.objects.create(task=task, author=self.employee, description="Nice work!", commented_by=self.employee)
        serializer = TaskCommentSerializer(instance=comment)
        self.assertEqual(serializer.data['description'], "Nice work!")
        self.assertEqual(serializer.data['author'], self.employee.user.username)
        self.assertEqual(serializer.data['commented_by'], self.employee.user.username)

    # ---------------- Folder Serializer ----------------
    def test_folder_serializer_read_only_fields(self):
        folder = Folder.objects.create(project=self.project, title="Root", description="Main", created_by=self.employee)
        serializer = FolderSerializer(instance=folder)
        self.assertEqual(serializer.data['path'], folder.path)
        self.assertIn('child_count', serializer.data)
        self.assertIn('lists_count', serializer.data)

    # ---------------- FolderFile Serializer ----------------
    def test_folder_file_serializer(self):
        folder = Folder.objects.create(project=self.project, title="Docs", description="Docs Folder", created_by=self.employee)
        file = SimpleUploadedFile("design.pdf", b"PDF data")
        ffile = FolderFile.objects.create(folder=folder, uploaded_by=self.employee, file=file)
        serializer = FolderFileSerializer(instance=ffile)
        self.assertEqual(serializer.data['folder'], folder.id)
        self.assertGreater(ffile.size_bytes, 0)

    # ---------------- List Serializer ----------------
    def test_list_serializer(self):
        folder = Folder.objects.create(project=self.project, title="Docs", description="Docs Folder", created_by=self.employee)
        lst = List.objects.create(project=self.project, folder=folder, name="Sprint 1")
        serializer = ListSerializer(instance=lst)
        self.assertEqual(serializer.data['name'], "Sprint 1")
        self.assertEqual(serializer.data['folder'], folder.id)
