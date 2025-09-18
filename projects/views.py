from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from .models import * 
from .serializers import *
from django.db.models import Count
from employee.models import * 
from django.core.exceptions import PermissionDenied
from rest_framework import viewsets, permissions
from employee.permissions import *
from django_filters.rest_framework import DjangoFilterBackend
from .models import Project, ProjectDocuments
from .serializers import *
from employee.models import Employee
from .permissions import *  
from django.db.models import Min
from employee.permissions import *


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.annotate(
        earliest_deadline = Min('end_date')
    )
    serializer_class = ProjectSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAssignedEmployeeOrReviewer]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'priority']
    ordering = ['name']

    def get_queryset(self):
        """
        Filter projects based on employee role:
        - HR/Admin: all projects
        - Project Manager: projects they manage
        - Team Lead: projects they lead
        - Employee: projects they are assigned to
        """
        employee = getattr(self.request.user, "employee_profile", None)
        if not employee:
            return Project.objects.none()

        role = employee.role
        if role in [Employee.HR, Employee.ADMIN]:
            return Project.objects.all()
        elif role == Employee.PROJECT_MANAGER:
            return Project.objects.filter(manager=employee)
        elif role == Employee.TEAM_LEAD:
            return Project.objects.filter(team_lead=employee)
        elif role == Employee.EMPLOYEE:
            return Project.objects.filter(members=employee)
        return Project.objects.none()

    def perform_create(self, serializer):
        """
        Automatically assign the logged-in user as the creator.
        If the creator is a project manager, they are also assigned as the manager.
        """
        employee = getattr(self.request.user, "employee_profile", None)
        if not employee:
            return Response({"error": "Invalid user"}, status=status.HTTP_400_BAD_REQUEST)

        role = getattr(employee, "role", None)
        if role == Employee.PROJECT_MANAGER:
            serializer.save(created_by=employee, manager=employee)
        else:
            serializer.save(created_by=employee)

    @action(detail=True, methods=['post'])
    def assign_members(self, request, pk=None):
        """
        Assign or update project members.
        """
        project = self.get_object()
        serializer = ProjectMemberUpdateSerializer(project, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Members updated successfully"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def assign_manager(self, request, pk=None):
        """
        Assign a project manager (for HR/Admin only).
        """
        employee = getattr(request.user, "employee_profile", None)
        if not employee or employee.role not in [Employee.HR, Employee.ADMIN]:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        project = self.get_object()
        manager_id = request.data.get("manager_id")
        if not manager_id:
            return Response({"error": "manager_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            manager = Employee.objects.get(id=manager_id, role=Employee.PROJECT_MANAGER)
        except Employee.DoesNotExist:
            return Response({"error": "Invalid manager"}, status=status.HTTP_400_BAD_REQUEST)

        project.manager = manager
        project.save()
        return Response({"message": "Manager assigned successfully"}, status=status.HTTP_200_OK)

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
    permission_classes = [IsAuthenticated, IsAssignedEmployeeOrReviewer, IsProjectManagerOrSuperUserOrHR ]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'assigned_to__user__first_name', 'assigned_to__user__last_name']
    ordering_fields = ['title', 'status', 'priority', 'due_date']
    ordering = ['title']
    filterset_fields = ['status', 'priority', 'assigned_to', 'project']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Tasks.objects.none()

        employee = getattr(user, "employee_profile", None)
        if not employee:
            return Tasks.objects.none()
        # Base queryset
        queryset = Tasks.objects.all()

        # Apply nested filter if project_pk exists
        project_id = self.kwargs.get('project_pk')  # Provided by nested router
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        # RBAC: HR / ADMIN / PM / TEAM_LEAD -> all tasks
        if employee.role in [Employee.HR, Employee.ADMIN, Employee.PROJECT_MANAGER, Employee.TEAM_LEAD]:
            return queryset

        # Regular employee -> only their tasks
        return queryset.filter(assigned_to=employee)
    
    def perform_create(self, serializer):
        employee = getattr(self.request.user, "employee_profile", None)
        project = Project.objects.get(pk=self.kwargs.get("project_pk"))
        serializer.save(created_by=employee, project=project)


    def perform_update(self, serializer):
        """Handle task review workflow"""
        task = serializer.instance
        status_value = self.request.data.get("status")

        employee = getattr(self.request.user, "employee_profile", None)

        # Assigned employee submits for review
        if status_value == "review" and employee == task.assigned_to:
            task.status = "review"

        # PM / TL / HR / Admin approves and marks as completed
        elif status_value == "completed" and employee and employee.role in ["PROJECT_MANAGER", "TEAM_LEAD", "HR", "ADMIN"]:
            task.status = "completed"
            task.reviewed_by = employee

        task.save()
        serializer.save()

class IsProjectAuthorized(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:   
            return False

        employee = getattr(request.user, "employee_profile", None)
        if not employee:
            return False

        if view.action == "create":
            return employee.role in [Employee.HR, Employee.ADMIN, Employee.PROJECT_MANAGER]

        return True

class TaskCommentViewSet(viewsets.ModelViewSet):
    serializer_class = TaskCommentSerializer
    permission_classes = [IsSelfOrTeamLeadOrHROrPMOrADMIN]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    def get_queryset(self):
        user = self.request.user

        if user.employee.role in ["HR", "PROJECT_MANAGER", "ADMIN", "TEAM_LEAD"]:
            return TaskComment.objects.all().order_by("id")

        return TaskComment.objects.filter(task__assigned_to=user).order_by("id")

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

        
class FolderViewSet(viewsets.ModelViewSet):
    queryset = Folder.objects.all().select_related("project", 'parent').annotate(
        child_count = Count("child"), lists_counts = Count("lists")
    )
    serializer_class = FolderSerializer
    permission_classes = [IsProjectManagerOrSuperUserOrHR, IsAssignedEmployeeOrReviewer]
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

    """
    method to create the folder
    not override in http_method_names
    """
    def perform_create(self, serializer):
        employee = getattr(self.request.user, 'employee_profile', None)
        if not employee:
            raise PermissionDenied("You are not an employee and cannot create folders.")
        
        if employee.role not in [Employee.PROJECT_MANAGER, Employee.ADMIN, Employee.HR]:
            raise PermissionDenied("You are not allowed to create folders.")
    
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
    @action(detail = True, methods = ['post'],permission_classes = [IsProjectManagerOrSuperUserOrHR]) #this endpoint only accepts POST requests.
    @transaction.atomic
    def move(self, request, pk = None):
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
    @action(detail = True, methods = ['post'], permission_classes = [IsProjectManagerOrSuperUserOrHR])
    def archive(self, request, pk = None):
        folder = self.get_object()
        folder.is_archived = True
        folder.is_deleted = False
        folder.save()
        return Response(self.get_serializer(folder).data)
    
    """
    Restores a folder from archived/deleted state.
    """
    @action(detail = True, methods = ['post'],permission_classes = [IsProjectManagerOrSuperUserOrHR])
    def restore(self, request, pk = None):
        folder = self.get_object()
        folder.is_archived = False
        folder.is_deleted = False
        folder.save()
        return Response(self.get_serializer(folder).data)
    
    """
    Marks a folder as deleted (but doesn’t remove it permanently).
    """
    @action(detail = True, methods = ['delete'], permission_classes = [IsProjectManagerOrSuperUserOrHR])
    def soft_delete(self, request, pk = None):
        folder = self.get_object()
        folder.is_deleted = True
        folder.save()
        return Response(status = status.HTTP_204_NO_CONTENT)
    
    """
    views the list of folders/projects
    [root > project > subfolder > current]
    """
    @action(detail = True,methods = ['get'], permission_classes = [IsProjectAuthorized])
    def subtree(self, request, pk = None):
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
    def children(self, request, pk = None):
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
    permission_classes = [IsProjectManagerOrSuperUserOrHR]
    """
    return the folder id to project assigned employee"""
    def get_queryset(self):
        qs = super().get_queryset().order_by('id')
        folder_id = self.request.query_params.get("folder")
        if folder_id:
            qs = qs.filter(folder_id = folder_id)
        return qs