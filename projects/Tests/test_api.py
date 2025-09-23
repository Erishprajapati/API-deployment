from django.test import TestCase
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
from employee.models import User, Employee, Department, EmployeeStatus
from projects.models import Project, Folder, FolderFile
from datetime import date

class FolderFileViewSetTests(TestCase):
    def setUp(self):
        # Create user and employee
        self.user = User.objects.create_user(username="admin@mail.com", email="admin@mail.com", password="pass123")
        self.department = Department.objects.create(name="IT")
        self.status = EmployeeStatus.objects.create(is_active=True)
        self.employee = Employee.objects.create(
            user=self.user,
            phone="9812345670",
            department=self.department,
            date_of_joining=date(2025, 1, 1),
            employee_status=self.status,
            role=Employee.PROJECT_MANAGER
        )

        # Create project and folder
        self.project = Project.objects.create(
            name="ERP", department=self.department,
            manager=self.employee, team_lead=self.employee,
            created_by=self.employee
        )
        self.folder = Folder.objects.create(
            project=self.project,
            title="Docs",
            description="Documents",
            created_by=self.employee
        )

        # Setup API client and login
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_upload_file(self):
        file = SimpleUploadedFile("design.pdf", b"PDF data")
        response = self.client.post("/api/folderfiles/", {"folder": self.folder.id, "file": file, "name": "Design Doc"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(FolderFile.objects.count(), 1)
        ffile = FolderFile.objects.first()
        self.assertEqual(ffile.folder, self.folder)
        self.assertEqual(ffile.uploaded_by, self.employee)

    def test_list_files_by_folder(self):
        ffile = FolderFile.objects.create(folder=self.folder, uploaded_by=self.employee, file=SimpleUploadedFile("a.txt", b"abc"), name="a.txt")
        response = self.client.get(f"/api/folderfiles/?folder={self.folder.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "a.txt")

    def test_move_file(self):
        ffile = FolderFile.objects.create(folder=self.folder, uploaded_by=self.employee, file=SimpleUploadedFile("b.txt", b"data"), name="b.txt")
        new_folder = Folder.objects.create(project=self.project, title="NewFolder", description="New", created_by=self.employee)
        response = self.client.post(f"/api/folderfiles/{ffile.id}/move/", {"new_folder": new_folder.id})
        self.assertEqual(response.status_code, 200)
        ffile.refresh_from_db()
        self.assertEqual(ffile.folder, new_folder)

    def test_delete_file(self):
        ffile = FolderFile.objects.create(folder=self.folder, uploaded_by=self.employee, file=SimpleUploadedFile("c.txt", b"data"), name="c.txt")
        response = self.client.delete(f"/api/folderfiles/{ffile.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(FolderFile.objects.count(), 0)
