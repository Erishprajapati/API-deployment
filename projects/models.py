# Create your models here.
from django.db import models
from employee.models import *
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator

# Create your models here.

class Project(Timestamp):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='projects')
    """
    limiting to project manager only gives access to project managers
    """
    name = models.CharField(_('Name'),unique=True, max_length=255,db_index=True)
    description = models.TextField(_('Description'), blank= True, null = True)
    manager = models.ForeignKey(Employee, on_delete=models.SET_NULL, null = True, related_name="managed_projects", db_index=True)
    team_lead = models.ForeignKey(Employee, on_delete=models.SET_NULL, null = True, related_name="lead_projects", db_index=True)
    members = models.ManyToManyField(Employee, related_name="assigned_to", blank = True)
    start_date = models.DateTimeField(auto_now_add=True, db_index=True)
    end_date = models.DateTimeField(blank=True, null=True,db_index=True)
    created_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null = True, related_name="created_projects")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    

"""
Project documents like the contract between clients and head
functional requirements of client
database architecture made by project_manager are stored here 
"""
    
class ProjectDocuments(models.Model):
    #project is extracted from project class to link the documents in the project
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null = True, related_name = "documents", db_index=True)
    file = models.FileField(upload_to="project/documents") #TODO: can limit the size of documents while uploading
    description = models.TextField()
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.project.name
    


class Tasks(models.Model):
    STATUS_CHOICES = [
        ("todo", "To Do"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("review", "In Review")
    ]
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent")
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks", db_index=True)
    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    assigned_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name="tasks", db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="todo", db_index=True)
    start_date = models.DateTimeField(auto_now_add=True, db_index=True) 
    due_date = models.DateTimeField(blank=True, null=True, db_index=True) #TODO: due date in past should be checked
    created_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name="created_tasks")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium", db_index=True)
    """
    role based access[HR, SuperUser, TeamLead, Project_manager] can approve
    """
    reviewed_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_tasks", db_index=True)

    def __str__(self):
        return self.title

"""
when comments are made by group members in the assigned projects(HR, SuperUser, TeamLead, ProjectManager)
Tasks comment can be viewed by this class
"""
class TaskComment(models.Model):
    task = models.ForeignKey(Tasks, on_delete=models.CASCADE, related_name="comments", db_index=True)
    author = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="task_comments", db_index=True)
    description = models.TextField(db_index=True)
    commented_by = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="comment_creator", db_index=True)
    commented_at = models.DateTimeField(auto_now_add=True, db_index=True)
    mentions = models.ManyToManyField(Employee, related_name="mentioned_in_comments", blank = True, db_index=True)

    def __str__(self):
        return f"{self.author} on {self.task}: {self.description[:30]}..."


"""
each parent folder can contain sub folders(child folder)
IT Projects: Web design, App development
"""
class Folder(models.Model):
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null = True, db_index=True)
    parent = models.ForeignKey("self", null = True, blank = True, on_delete = models.CASCADE, related_name="child", db_index=True)
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    is_archived = models.BooleanField(default = False, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    path = models.TextField(blank = True, editable= False)
    created_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null = True, related_name="created_folders", db_index=True)
    created_at = models. DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now= True, db_index=True)
    
    class Meta:
        unique_together = (("project", "parent", "title"),)
        """helps to search in database fast:optimizes the database queries"""
        indexes = [
            models.Index(fields = ['project', 'parent', 'order']),
            models.Index(fields = ['project', 'path']),
            models.Index(fields = ['is_deleted', 'is_archived']),
        ]

    """
    saves the folder normally and collects the name from parent class and join it with 
    parent folder
    """
    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)
    #     parts = []
    #     node = self
    #     while node:
    #         parts.append(node.title)
    #         node = node.parent

    #     new_path = '/'.join(reversed(parts))
    #     if self.path != new_path:
    #         Folder.objects.filter(pk = self.pk).update(path = new_path) #this updates the path field only
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        parts = []
        node = self
        while node:
            parts.append(node.title)
            node = node.parent
        new_path = '/'.join(reversed(parts))
        if self.path != new_path:
            Folder.objects.filter(pk=self.pk).update(path=new_path)



    def __str__(self):
        return self.path or self.title
        

"""
view the list of project in parent folders 
"""
class List(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="lists", db_index=True)
    folder = models.ForeignKey(Folder, on_delete=models.PROTECT, related_name='lists', db_index=True)
    name = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default = 0) #TODO: how they appear in parent folder
    is_archieved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class FolderFile(models.Model):
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name="files", db_index=True)
    uploaded_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null = True, db_index=True)
    file = models.FileField(upload_to='Folder/Files')
    name = models.CharField(max_length=200, db_index=True)
    size_bytes = models.BigIntegerField(default = 0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, 'size'):
            self.size_bytes = self.file.size
        if not self.name:
            self.name = getattr(self.file, "name", self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name