# project/serializers.py
from rest_framework import serializers
from .models import *
from employee.serializers import *
from employee.models import Employee
# from employee.models import Employee

# class EmployeeSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Employee
#         fields = ['id', 'user', 'role', 'employee_code']

class ProjectDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDocuments
        fields = ['id', 'file', 'description', 'uploaded_at']

class ProjectSerializer(serializers.ModelSerializer):
    manager = EmployeeNestedMinimalSerializer(read_only=True)
    manager_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(), write_only=True, source='manager'
    )
    team_lead = EmployeeNestedMinimalSerializer(read_only=True)
    team_lead_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(), write_only=True, source='team_lead'
    )
    members = EmployeeNestedMinimalSerializer(read_only=True, many=True)
    member_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(), write_only=True, many=True, source='members', required=False
    )
    documents = ProjectDocumentSerializer(read_only=True, many=True)

    def validate_end_date(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("End date cannot be in the past.")
        return value

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'department',
            'manager', 'manager_ids', 'team_lead', 'team_lead_ids',
            'members', 'member_ids', 'documents',
            'start_date', 'end_date', 'is_active'
        ]


class ProjectMemberUpdateSerializer(serializers.ModelSerializer):
    members = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all(), many=True)

    class Meta:
        model = Project
        fields = ['members']

class ProjectDocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDocuments
        fields = ['project', 'file', 'description']
class TaskSerializer(serializers.ModelSerializer):
    assigned_to = EmployeeNestedMinimalSerializer(read_only=True)
    created_by = EmployeeNestedMinimalSerializer(read_only=True)
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())

    class Meta:
        model = Tasks
        fields = "__all__"
        read_only_fields = [
            'created_by', 'created_at', 'updated_at', 'start_date',
            'is_active', 'reviewed_by', 'submitted_at', 'status'
        ]

    def validate(self, data):
        project = data.get("project")
        title = data.get("title")

        if project and title and Tasks.objects.filter(project=project, title__iexact=title).exists():
            raise serializers.ValidationError(
                {"title": "A task with this title already exists in this project."}
            )

        due_date = data.get("due_date")
        if due_date:
            from django.utils import timezone
            if due_date < timezone.now():
                raise serializers.ValidationError(
                    {"due_date": "Due date cannot be in the past."}
                )

        return data

    def create(self, validated_data):
        """Attach created_by automatically"""
        request = self.context.get("request")
        employee = getattr(request.user, "employee_profile", None)
        if not employee:
            raise serializers.ValidationError({"detail": "User has no associated employee profile."})

        task = Tasks.objects.create(created_by=employee, **validated_data)
        return task

    def update(self, instance, validated_data):
        """
        Limit updates to editable fields only.
        """
        protected_fields = {
            'status', 'created_by', 'reviewed_by', 'submitted_at',
            'submission_notes', 'submission_file'
        }

        for attr, value in validated_data.items():
            if attr in protected_fields:
                # Ignore attempts to manually modify workflow fields
                continue
            setattr(instance, attr, value)

        instance.save()
        return instance


class ProjectEmployeeNestedSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()  # Only show name and email

    class Meta:
        model = Employee
        fields = ['id', 'user']

    def get_user(self, obj):
        return {
            "first_name": obj.user.first_name,
            "last_name": obj.user.last_name,
            "email": obj.user.email
        }
    
class TaskCommentSerializer(serializers.ModelSerializer):
    # mentions: get username of related users
    mentions = serializers.PrimaryKeyRelatedField(
    many=True,
    queryset=Employee.objects.all(),
    required=False
    )

    # author: read-only, get username via related User
    author = serializers.ReadOnlyField(source="author.user.username")
    
    # commented_by: read-only via Employee → User
    commented_by = serializers.ReadOnlyField(source="commented_by.user.username")

    class Meta:
        model = TaskComment
        fields = ["id", "task", "author", "description", "mentions", "commented_at", "commented_by"]

# class FolderSerializer(serializers.ModelSerializer):
#     child_count = serializers.IntegerField(read_only = True) #ensures the count are only viewable not editable
#     lists_count = serializers.IntegerField(read_only = True)
    
#     class Meta:
#         model = Folder
#         fields = "__all__"
#         read_only_fields = ["path", "created_at", "updated_at", "child_count", "lists_count"]
#         """to count the numbers"""
#     def get_child_count(self, obj):
#         return obj.child.count()

#     def get_lists_count(self, obj):
#         return obj.list_set.count()  # or

class FolderSerializer(serializers.ModelSerializer):
    child_count = serializers.SerializerMethodField()
    lists_count = serializers.SerializerMethodField()
    read_only_fields = ["uploaded_by", "created_at"]

    class Meta:
        model = Folder
        fields = "__all__"
        read_only_fields = ["path", "created_at", "updated_at", "child_count", "lists_count"]

    def get_child_count(self, obj):
        return obj.child.count()

    def get_lists_count(self, obj):
        return obj.lists.count()  # use the related_name of List model

class ListSerializer(serializers.ModelSerializer):
    class Meta:
        model = List
        fields = "__all__"

class FolderFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FolderFile
        fields = "__all__"
        read_only_fields = ['size_bytes', 'created_at']