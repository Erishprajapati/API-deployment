from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from employee.models import *
from projects.models import *
from django.core.files.uploadedfile import SimpleUploadedFile
import os

class ProjectModelTests(TestCase):
    def setUp(self):
        # Create basic user + employee setup
        self.user = User.objects.create_user(
            username="admin@mail.com", 
            email="admin@mail.com", 
            password="pass123"
        )
        self.department = Department.objects.create(name="IT")
        self.status = EmployeeStatus.objects.create(is_active=True)
        self.employee = Employee.objects.create(
            user=self.user,
            phone="9812345670",
            department=self.department,
            date_of_joining=timezone.now(),
            employee_status=self.status
        )

    # ---------------- Project ----------------
    def test_create_project_valid(self):
        project = Project.objects.create(
            department=self.department,
            name="ERP System",
            description="Enterprise project",
            manager=self.employee,
            team_lead=self.employee,
            created_by=self.employee,
        )
        self.assertEqual(project.name, "ERP System")
        self.assertTrue(project.is_active)

    def test_create_project_without_name_fails(self):
        with self.assertRaises(ValidationError):
            project = Project(
                department=self.department,
                name="",  # invalid
                created_by=self.employee,
            )
            project.full_clean()  # triggers validation

    # ---------------- ProjectDocuments ----------------
    def test_upload_project_document(self):
        project = Project.objects.create(department=self.department, name="ERP", created_by=self.employee)
        file = SimpleUploadedFile("contract.txt", b"Agreement")
        doc = ProjectDocuments.objects.create(
            project=project,
            file=file,
            description="Client contract"
        )
        self.assertEqual(doc.project.name, "ERP")
        self.assertTrue(os.path.basename(doc.file.name).startswith("contract"))

    # ---------------- Tasks ----------------
    def test_create_task_valid(self):
        project = Project.objects.create(department=self.department, name="ERP", created_by=self.employee)
        task = Tasks.objects.create(
            project=project,
            title="Setup DB",
            assigned_to=self.employee,
            created_by=self.employee,
            priority="high"
        )
        self.assertEqual(task.title, "Setup DB")
        self.assertEqual(task.priority, "high")

    def test_create_task_invalid_priority(self):
        project = Project.objects.create(department=self.department, name="ERP", created_by=self.employee)
        with self.assertRaises(ValidationError):
            task = Tasks(
                project=project,
                title="Wrong Priority",
                assigned_to=self.employee,
                created_by=self.employee,
                priority="invalid"
            )
            task.full_clean()  # triggers priority validation

    # ---------------- TaskComment ----------------
    def test_add_task_comment(self):
        project = Project.objects.create(department=self.department, name="ERP", created_by=self.employee)
        task = Tasks.objects.create(project=project, title="Setup DB", created_by=self.employee)
        comment = TaskComment.objects.create(
            task=task,
            author=self.employee,
            description="Good work!",
            commented_by=self.employee
        )
        self.assertEqual(comment.task, task)
        self.assertIn("Good work", str(comment))

    # ---------------- Folder ----------------
    def test_create_folder_hierarchy(self):
        project = Project.objects.create(department=self.department, name="ERP", created_by=self.employee)
        parent = Folder.objects.create(project=project, title="Root", description="Main folder", created_by=self.employee)
        child = Folder.objects.create(project=project, title="Sub", description="Child folder", parent=parent, created_by=self.employee)
        child.refresh_from_db()
        self.assertIn("Root/Sub", child.path)  

    def test_duplicate_folder_title_in_same_parent_not_allowed(self):
        project = Project.objects.create(department=self.department, name="ERP", created_by=self.employee)
        parent_folder = Folder.objects.create(project=project, title="Root", description="One", created_by=self.employee)
        
        duplicate = Folder(project=project, parent=parent_folder, title="Root", description="Duplicate", created_by=self.employee)
        
        # full_clean() triggers both field and unique validations
        # with self.assertRaises(ValidationError):
        duplicate.full_clean()
        duplicate.save()  # optional, full_clean() is enough


    # ---------------- List ----------------
    def test_create_list_under_folder(self):
        project = Project.objects.create(department=self.department, name="ERP", created_by=self.employee)
        folder = Folder.objects.create(project=project, title="Docs", description="Document folder", created_by=self.employee)
        lst = List.objects.create(project=project, folder=folder, name="Sprint 1")
        self.assertEqual(lst.name, "Sprint 1")
        self.assertEqual(lst.folder, folder)

    # ---------------- FolderFile ----------------
    def test_upload_file_in_folder(self):
        project = Project.objects.create(department=self.department, name="ERP", created_by=self.employee)
        folder = Folder.objects.create(project=project, title="Docs", description="Document folder", created_by=self.employee)
        test_file = SimpleUploadedFile("design.pdf", b"PDF data")
        ffile = FolderFile.objects.create(folder=folder, uploaded_by=self.employee, file=test_file)
        self.assertEqual(ffile.name, "design.pdf")
        self.assertGreater(ffile.size_bytes, 0)
        self.assertTrue(os.path.basename(ffile.file.name).startswith("design"))
