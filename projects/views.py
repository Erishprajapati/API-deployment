from rest_framework import viewsets, status, filters, permissions
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import * 
from .serializers import *
from django.db.models import Min, Q, BooleanField, ExpressionWrapper, Count
from employee.models import * 
from django.core.exceptions import PermissionDenied
from employee.permissions import *
from django_filters.rest_framework import DjangoFilterBackend
from .models import Project, ProjectDocuments
from .serializers import *
from employee.models import Employee
from .permissions import *
from django.db.models import Min
from employee.permissions import *
from .tasks import *
from .tasks import send_task_created_email

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAssignedProjectOrHigher]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'priority', 'earliest_deadline']
    ordering = ['name']

    def get_queryset(self):
        """
        Role-based project filtering + overdue project highlighting
        """
        employee = getattr(self.request.user, "employee_profile", None)
        if not employee:
            return Project.objects.none()

        today = timezone.now().date()

        queryset = Project.objects.annotate(
        earliest_due_date=Min('tasks__due_date')  #use 'tasks' because of related_name="tasks"
        ).annotate(
            is_overdue=ExpressionWrapper(
                Q(earliest_due_date__lt=today),
                output_field=BooleanField()
            )
        )
        # Role-based filtering
        role = employee.role
        if role in [Employee.HR, Employee.ADMIN]:
            queryset = queryset.all()
        elif role == Employee.PROJECT_MANAGER:
            queryset = queryset.filter(manager=employee)
        elif role == Employee.TEAM_LEAD:
            queryset = queryset.filter(team_lead=employee)
        elif role == Employee.EMPLOYEE:
            queryset = queryset.filter(members=employee)
        else:
            return Project.objects.none()

        # Role-based ordering
        if role == Employee.EMPLOYEE:
            queryset = queryset.order_by('earliest_due_date')
        else:
            queryset = queryset.order_by('name')
        return queryset

    def perform_create(self, serializer):
        end_date = serializer.validated_data.get('end_date')
        if end_date and end_date < timezone.now():
            raise serializers.ValidationError({"end_date": "End date cannot be in the past."})

        employee = getattr(self.request.user, "employee_profile", None)
        if not employee:
            raise serializers.ValidationError({"error": "Invalid user"})

        role = getattr(employee, "role", None)

        # Only save once
        project = serializer.save(
            created_by=employee,
            manager=employee if role == Employee.PROJECT_MANAGER else None
        )

        # Send email asynchronously
        subject = f"New Project Created: {project.name}"
        message = f"Hello {employee.user.first_name}, your project '{project.name}' has been created successfully."
        send_assignment_email.delay(subject, message, employee.user.email)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        project_name = instance.name
        self.perform_destroy(instance)
        return Response(
            {"message": f"Project '{project_name}' has been deleted successfully."},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def assign_members(self, request, pk=None):
        project = self.get_object()
        member_ids = request.data.get('member_ids', [])

        if not isinstance(member_ids, list):
            return Response(
                {"error": "member_ids must be a list of employee IDs."},
                status=status.HTTP_400_BAD_REQUEST
            )
        employees = Employee.objects.filter(id__in=member_ids)
        if len(employees) != len(member_ids):
            return Response(
                {"error": "One or more invalid employee IDs."},
                status=status.HTTP_400_BAD_REQUEST)
        project.members.set(employees)

        # Notify new members via email (async)
        for emp in employees:
            if emp.user and emp.user.email:
                subject = f"Added to Project: {project.name}"
                message = (
                    f"Hi {emp.user.first_name},\n\n"
                    f"You have been added to the project '{project.name}'.\n"
                    f"Project Description: {project.description or 'No description'}\n\n"
                    "Best,\nProject Management System"
                )
                send_assignment_email.delay(subject, message, emp.user.email)

        return Response(
            {"message": "Members assigned successfully and notified via email."},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def assign_manager(self, request, pk=None):
        """
        Assign a project manager (HR/Admin only).
        Expects: {"manager_id": 9}
        """
        employee = getattr(request.user, "employee_profile", None)
        if not employee or employee.role not in [Employee.HR, Employee.ADMIN]:
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        project = self.get_object()
        manager_id = request.data.get("manager_id")

        if not manager_id:
            return Response(
                {"error": "manager_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            manager = Employee.objects.get(id=manager_id, role=Employee.PROJECT_MANAGER)
        except Employee.DoesNotExist:
            return Response(
                {"error": "Invalid manager ID or user is not a Project Manager."},
                status=status.HTTP_400_BAD_REQUEST
            )

        project.manager = manager
        project.save(update_fields=['manager'])

        # Send notification email (async)
        if manager.user and manager.user.email:
            subject = f"You've been assigned as Project Manager for '{project.name}'"
            message = (
                f"Hi {manager.user.first_name},\n\n"
                f"You have been assigned as the Project Manager for the project '{project.name}'.\n"
                f"Description: {project.description or 'No description'}\n\n"
                f"Please log in to the system to view the full project details.\n\n"
                f"Best Regards,\nProject Management System"
            )
            send_assignment_email.delay(subject, message, manager.user.email)

        return Response(
            {"message": f"Manager '{manager.user.first_name}' assigned and notified via email."},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def upload_document(self, request, pk=None):
        """
        Upload documents to a project.
        """
        project = self.get_object()
        serializer = ProjectDocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(project=project)  # Associate the document with the project
        return Response({"message": "Document uploaded successfully"}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        """
        List all documents of the project.
        """
        project = self.get_object()
        documents = ProjectDocuments.objects.filter(project=project)
        serializer = ProjectDocumentSerializer(documents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Tasks.objects.all()
    serializer_class = TaskSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAssignedEmployeeOrReviewer]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'assigned_to__user__first_name', 'assigned_to__user__last_name']
    ordering_fields = ['title', 'status', 'priority', 'due_date']
    ordering = ['title']
    filterset_fields = ['status', 'priority', 'assigned_to', 'project']

    def get_queryset(self):
        user = self.request.user
        if getattr(self, 'swagger_fake_view', False) or not user.is_authenticated:
            return Tasks.objects.none()
        queryset = super().get_queryset()
        project_id = self.kwargs.get('project_pk')
        employee = getattr(user, "employee_profile", None)

        if employee and employee.role in [Employee.HR, Employee.PROJECT_MANAGER, Employee.TEAM_LEAD, Employee.ADMIN]:
            if project_id:
                queryset = queryset.filter(project_id=project_id)
            return queryset.order_by('-created_at')

        if employee:
            if project_id:
                queryset = queryset.filter(project_id=project_id)
            return queryset.filter(assigned_to=employee).order_by('-created_at')

        return Tasks.objects.none()

    def perform_create(self, serializer):
        employee = getattr(self.request.user, "employee_profile", None)
        project = Project.objects.get(pk=self.kwargs.get("project_pk"))
        task = serializer.save(created_by=employee, project=project)
        send_task_created_email.delay(task.id)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": f"Task '{instance.title}' has been deleted successfully."},
            status=status.HTTP_200_OK
    )

    @action(detail=True, methods=['post'])
    def submit(self, request, project_pk=None, pk = None, **kwargs):
        task = self.get_object()
        employee = getattr(request.user, "employee_profile", None)

        if not employee or task.assigned_to_id != employee.id:
            return Response({"detail": "You cannot submit a task not assigned to you."}, status=403)

        # Prevent multiple submissions if already under review or completed
        if task.status in ["review", "completed", "cancelled"]:
            return Response(
                {"detail": f"Task cannot be submitted in its current status: {task.status}."},
                status=400
            )

        task.status = "review"
        task.submitted_at = timezone.now()
        task.submission_notes = request.data.get("submission_notes", "")
        if "submission_file" in request.FILES:
            task.submission_file = request.FILES["submission_file"]
        task.save()

        return Response({"message": "Task submitted for review."}, status=200)
    @action(detail=True, methods=['post'])
    def approve(self, request, project_pk=None, pk = None):
        task = self.get_object()
        employee = getattr(request.user, "employee_profile", None)

        if employee.role not in [Employee.HR, Employee.ADMIN, Employee.PROJECT_MANAGER, Employee.TEAM_LEAD]:
            return Response({"detail": "You are not authorized to approve this task."}, status=403)

        if task.status != "review":
            return Response({"detail": "Task must be in review before approving."}, status=400)

        task.status = "completed"
        task.reviewed_by = employee
        # Optional: store approval note if provided
        approval_note = request.data.get("approval_note")
        if approval_note:
            task.submission_notes = approval_note
        task.save()
        return Response({"message": "Task approved and marked as completed."}, status=200)


    @action(detail=True, methods=['patch'], url_path="cancel")
    def cancel_task(self, request, project_pk = None, pk=None, **kwargs):
        task = self.get_object()
        employee = getattr(request.user, "employee_profile", None)

        if not employee:
            return Response({"detail": "No employee profile found."}, status=403)

        if employee.role not in [Employee.HR, Employee.ADMIN, Employee.PROJECT_MANAGER, Employee.TEAM_LEAD]:
            if task.assigned_to != employee:
                return Response({"detail": "You can only cancel your own tasks."}, status=403)

        if task.status not in ["todo", "in_progress"]:
            return Response({"detail": "Only tasks not yet submitted or in progress can be cancelled."}, status=400)

        task.status = "cancelled"
        task.save(update_fields=["status"])
        return Response({"message": "Task cancelled successfully."}, status=200)

    @action(detail=True, methods=['patch'], url_path="reject")
    def reject_task(self, request,project_pk = None, pk=None, **kwargs):
        task = self.get_object()
        employee = getattr(request.user, "employee_profile", None)

        if not employee or employee.role not in [Employee.HR, Employee.ADMIN, Employee.PROJECT_MANAGER, Employee.TEAM_LEAD]:
            return Response({"detail": "You are not authorized to reject this task."}, status=403)

        if task.status != "review":
            return Response({"detail": "Only tasks under review can be rejected."}, status=400)

        task.status = "rejected"
        task.reviewed_by = employee
        task.save()
        return Response({"message": "Task rejected successfully."}, status=200)

    @action(detail=False, methods=['post'], permission_classes=[IsHROrAdminOrProjectManager])
    def trigger_overdue_check(self, request, **kwargs):
        check_overdue_tasks.delay()
        return Response({"message": "Overdue check triggered"}, status=200)

class TaskCommentViewSet(viewsets.ModelViewSet):
    serializer_class = TaskCommentSerializer
    permission_classes = [IsSelfOrTeamLeadOrHROrPMOrADMIN]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    def get_queryset(self):
        user = self.request.user
        employee = getattr(user, "employee_profile", None)

        if employee is None:
            return TaskComment.objects.none()  # No Employee profile → no comments

        # Higher roles can see all comments
        if employee.role in [Employee.HR, Employee.PROJECT_MANAGER, Employee.ADMIN, Employee.TEAM_LEAD]:
            return TaskComment.objects.all().order_by("id")

        # Normal assigned employees → only comments on their tasks
        return TaskComment.objects.filter(task__assigned_to=employee).order_by("id")



    def perform_create(self, serializer):
        if not hasattr(self.request.user, 'employee_profile'):
            raise serializers.ValidationError("This user is not linked to an Employee profile.")

        employee = self.request.user.employee_profile
        serializer.save(author=employee, commented_by=employee)        
class FolderViewSet(viewsets.ModelViewSet):
    queryset = Folder.objects.all().select_related("project", 'parent').annotate(
        child_count = Count("child"), lists_counts = Count("lists")
    )
    serializer_class = FolderSerializer
    permission_classes = [IsHROrAdminOrProjectManager, IsAssignedEmployeeOrReviewer]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    
    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False)

        # get project id from URL instead of query params
        project_id = self.kwargs.get('project_pk')
        if project_id:
            qs = qs.filter(project_id=project_id)

        parent_id = self.request.query_params.get('parent')
        search = self.request.query_params.get('q')

        if parent_id:
            qs = qs.filter(parent_id=parent_id)

        if search:
            qs = qs.filter(name__icontains=search)

        return qs.order_by('order', 'id')
    @action(detail=True, methods=["post"], permission_classes=[IsHROrAdminOrProjectManager])
    def move(self, request, pk=None):
        file = self.get_object()
        new_folder_id = request.data.get("new_folder")
        if not new_folder_id:
            return Response({"error": "new_folder is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_folder = Folder.objects.get(pk=new_folder_id, project=file.folder.project)
        except Folder.DoesNotExist:
            return Response({"error": "Invalid folder"}, status=status.HTTP_400_BAD_REQUEST)

        file.folder = new_folder
        file.save()
        return Response(self.get_serializer(file).data, status=status.HTTP_200_OK)

    """
    method to create the folder
    not override in http_method_names
    """
    # def perform_create(self, serializer):
    #     employee = getattr(self.request.user, 'employee_profile', None)
    #     if not employee:
    #         raise PermissionDenied("You are not an employee and cannot create folders.")
        
    #     if employee.role not in [Employee.PROJECT_MANAGER, Employee.ADMIN, Employee.HR]:
    #         raise PermissionDenied("You are not allowed to create folders.")
    
    #     serializer.save(created_by=employee)
    def perform_create(self, serializer):
        employee = getattr(self.request.user, "employee_profile", None)
        if not employee:
            raise PermissionDenied("Only employees can upload files.")
        serializer.save(created_by=employee)

    def update(self, request, *args, **kwargs):
        employee = getattr(request.user, 'employee_profile', None)
        if not employee or employee.role not in [Employee.PROJECT_MANAGER, Employee.ADMIN]:
            raise PermissionDenied("You are not allowed to update folders.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        employee = getattr(request.user, 'employee_profile', None)
        if not employee or employee.role not in [Employee.PROJECT_MANAGER, Employee.ADMIN]:
            raise PermissionDenied("You are not allowed to delete folders.")
        
        return super().destroy(request, *args, **kwargs)

    """
    Custom endpoints for viewse
    More than CRUD operations
    """
    @action(detail = True, methods = ['post'],permission_classes = [IsHROrAdminOrProjectManager]) #this endpoint only accepts POST requests.
    @transaction.atomic
    def move(self, request, project_pk = None, pk = None):
        """access to folder by primary key"""
        folder = self.get_object()
        #Finds the new parent.
        new_parent_id = request.data.get("new_parent", None)
        new_parent = None
        if new_parent_id is not None:
            new_parent = Folder.objects.get(pk = new_parent_id, project = folder.project, is_deleted= False)

            """prevent moving into its own subtree"""
            if new_parent.path.startswith((folder.path + "/")) or new_parent.pk == folder.pk:
                return Response({"detail": "Cannot move a folder into its own subtree."},
                                status=status.HTTP_400_BAD_REQUEST)
        folder.parent = new_parent
        if "new_order" in request.data:
            folder.order = int(request.data['new_order'])
        folder.save()
        return Response(self.get_serializer(folder).data)

    """
    Marks a folder as archived (is_archived = True).
    """
    @action(detail = True, methods = ['post'], permission_classes = [IsHROrAdminOrProjectManager])
    def archive(self, request,project_pk = None, pk = None):
        folder = self.get_object()
        folder.is_archived = True
        folder.is_deleted = False
        folder.save()
        return Response(self.get_serializer(folder).data)
    
    """
    Restores a folder from archived/deleted state.
    """
    @action(detail = True, methods = ['post'],permission_classes = [IsHROrAdminOrProjectManager])
    def restore(self, request, project_pk = None,pk = None):
        folder = self.get_object()
        folder.is_archived = False
        folder.is_deleted = False
        folder.save()
        return Response(self.get_serializer(folder).data)
    
    """
    Marks a folder as deleted (but doesn’t remove it permanently).
    """
    @action(detail = True, methods = ['delete'], permission_classes = [IsHROrAdminOrProjectManager])
    def soft_delete(self, request, project_pk = None, pk = None):
        folder = self.get_object()
        folder.is_deleted = True
        folder.save()
        return Response(status = status.HTTP_204_NO_CONTENT)
    @action(detail = True,methods = ['get'], permission_classes = [IsProjectAuthorized])
    def subtree(self, request, project_pk = None, pk = None):
        node = self.get_object()
        tree = []
        while node:
            tree.append({"id" : node.id, "name": node.name})
            node = node.parent
        return Response(list(reversed(tree)))
    
    """
    Returns all subfolders under the current folder.
    """
    @action(detail = True, methods = ['get'], permission_classes = [IsProjectAuthorized])
    def children(self, request,project_pk = None, pk = None):
        node = self.get_object()
        children = self.get_queryset().filter(parent = node)
        return Response(self.get_serializer(children, many = True).data)
    
class ListViewSet(viewsets.ModelViewSet):
    queryset = List.objects.all().select_related('project', 'folder')
    serializer_class = ListSerializer
    permission_classes = [IsProjectAuthorized]
class FolderFileViewSet(viewsets.ModelViewSet):
    queryset = FolderFile.objects.all()
    serializer_class = FolderFileSerializer
    permission_classes = [IsHROrAdminOrProjectManager]
    """
    return the folder id to project assigned employee"""
    def get_queryset(self):
        qs = super().get_queryset().order_by('id')
        folder_id = self.request.query_params.get("folder")
        if folder_id:
            qs = qs.filter(folder_id = folder_id)
        return qs