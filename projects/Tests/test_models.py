# projects/tests/test_models.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
import os
from employee.models import Department, Employee
from projects.models import Project, ProjectDocuments, Tasks, TaskComment, Folder, List, FolderFile
from django.contrib.auth import get_user_model
from unittest.mock import patch

User = get_user_model()


@patch('projects.tasks.send_task_created_email.delay')
class ProjectModelTests(TestCase):
    def setUp(self):
        """Create a valid Employee with all required fields."""
        self.user = User.objects.create_user(
            email="admin@example.com",
            username="admin@example.com",
            password="securepass123"
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

    # ---------------- Project ----------------
    def test_create_project_valid(self, mock_send_email):
        """A valid project should be created with required fields."""
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

    def test_create_project_without_name_fails(self, mock_send_email):
        """Project name is required and must be non-empty."""
        with self.assertRaises(ValidationError):
            project = Project(
                department=self.department,
                name="",  # Invalid: blank name
                created_by=self.employee,
            )
            project.full_clean()

    def test_project_unique_name(self, mock_send_email):
        """Project names must be unique."""
        Project.objects.create(
            department=self.department,
            name="Unique Project",
            created_by=self.employee
        )
        with self.assertRaises(ValidationError):
            duplicate = Project(
                department=self.department,
                name="Unique Project",  # Duplicate
                created_by=self.employee
            )
            duplicate.full_clean()

    # ---------------- ProjectDocuments ----------------
    def test_upload_project_document(self, mock_send_email):
        """A document can be uploaded and linked to a project."""
        project = Project.objects.create(
            department=self.department,
            name="ERP",
            created_by=self.employee
        )
        file = SimpleUploadedFile("contract.pdf", b"Client agreement content")
        doc = ProjectDocuments.objects.create(
            project=project,
            file=file,
            description="Signed client contract"
        )
        self.assertEqual(doc.project.name, "ERP")
        self.assertIn("contract", os.path.basename(doc.file.name))

    # ---------------- Tasks ----------------
    def test_create_task_valid(self, mock_send_email):
        """A task can be created with valid fields."""
        project = Project.objects.create(
            department=self.department,
            name="ERP",
            created_by=self.employee
        )
        task = Tasks.objects.create(
            project=project,
            title="Setup Database",
            assigned_to=self.employee,
            created_by=self.employee,
            priority="high"
        )
        self.assertEqual(task.title, "Setup Database")
        self.assertEqual(task.priority, "high")
        mock_send_email.assert_called_once_with(task.id)

    def test_create_task_invalid_priority(self, mock_send_email):
        """Task priority must be one of the allowed choices."""
        project = Project.objects.create(
            department=self.department,
            name="ERP",
            created_by=self.employee
        )
        with self.assertRaises(ValidationError):
            task = Tasks(
                project=project,
                title="Invalid Priority Task",
                assigned_to=self.employee,
                created_by=self.employee,
                priority="extreme"  # Not in PRIORITY_CHOICES
            )
            task.full_clean()

    def test_task_title_unique_per_project(self, mock_send_email):
        """Task titles must be unique within a project (case-insensitive)."""
        project = Project.objects.create(
            department=self.department,
            name="ERP",
            created_by=self.employee
        )
        Tasks.objects.create(
            project=project,
            title="Design UI",
            created_by=self.employee
        )
        with self.assertRaises(ValidationError):
            duplicate = Tasks(
                project=project,
                title="DESIGN UI",  # Same title, different case
                created_by=self.employee
            )
            duplicate.full_clean()

    # ---------------- TaskComment ----------------
    def test_add_task_comment(self, mock_send_email):
        """A comment can be added to a task by an employee."""
        project = Project.objects.create(
            department=self.department,
            name="ERP",
            created_by=self.employee
        )
        task = Tasks.objects.create(
            project=project,
            title="Setup DB",
            created_by=self.employee
        )
        comment = TaskComment.objects.create(
            task=task,
            author=self.employee,
            commented_by=self.employee,
            description="Great progress!"
        )
        self.assertEqual(comment.task, task)
        self.assertIn("Great progress", str(comment))

    # ---------------- Folder ----------------
    def test_create_folder_hierarchy(self, mock_send_email):
        """Folders can be nested, and the path reflects the full hierarchy."""
        project = Project.objects.create(
            department=self.department,
            name="ERP",
            created_by=self.employee
        )
        root = Folder.objects.create(
            project=project,
            title="Root",
            description="Main folder",
            created_by=self.employee
        )
        child = Folder.objects.create(
            project=project,
            parent=root,
            title="Subfolder",
            description="Nested folder",
            created_by=self.employee
        )
        child.refresh_from_db()
        self.assertEqual(child.path, "Root/Subfolder")

    def test_duplicate_folder_title_same_parent_not_allowed(self, mock_send_email):
        """Two folders cannot have the same title under the same parent in the same project."""
        project = Project.objects.create(
            department=self.department,
            name="ERP",
            created_by=self.employee
        )
        parent = Folder.objects.create(
            project=project,
            title="Parent",
            description="Parent folder",
            created_by=self.employee
        )
        Folder.objects.create(
            project=project,
            parent=parent,
            title="Child",
            description="First child",
            created_by=self.employee
        )
        with self.assertRaises(ValidationError):
            duplicate = Folder(
                project=project,
                parent=parent,
                title="Child",  # Same title under same parent
                description="Second child",
                created_by=self.employee
            )
            duplicate.full_clean()

    # ---------------- List ----------------
    def test_create_list_under_folder(self, mock_send_email):
        """A list (e.g., task board) can be created inside a folder."""
        project = Project.objects.create(
            department=self.department,
            name="ERP",
            created_by=self.employee
        )
        folder = Folder.objects.create(
            project=project,
            title="Docs",
            description="Document folder",
            created_by=self.employee
        )
        lst = List.objects.create(
            project=project,
            folder=folder,
            name="Sprint 1"
        )
        self.assertEqual(lst.name, "Sprint 1")
        self.assertEqual(lst.folder, folder)

    # ---------------- FolderFile ----------------
    def test_upload_file_in_folder(self, mock_send_email):
        """Files can be uploaded into a folder with auto-captured metadata."""
        project = Project.objects.create(
            department=self.department,
            name="ERP",
            created_by=self.employee
        )
        folder = Folder.objects.create(
            project=project,
            title="Designs",
            description="UI mockups",
            created_by=self.employee
        )
        test_file = SimpleUploadedFile("mockup.png", b"PNG image data")
        ffile = FolderFile.objects.create(
            folder=folder,
            uploaded_by=self.employee,
            file=test_file
        )
        self.assertEqual(ffile.name, "mockup.png")
        self.assertGreater(ffile.size_bytes, 0)
        self.assertIn("mockup", os.path.basename(ffile.file.name))