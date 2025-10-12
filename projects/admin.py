from django.contrib import admin
from .models import *
from .tasks import * 
# Register your models here.
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'manager', 'team_lead', 'start_date', 'created_at', 'created_by', 'end_date', 'updated_at')

    def save_model(self, request, obj, form, change):
        is_new = not change  # True if creating a new project
        super().save_model(request, obj, form, change)

        if is_new and obj.created_by:
            subject = f"New Project Created: {obj.name}"
            message = f"Hi {obj.created_by.user.first_name}, your project '{obj.name}' has been created successfully."
            send_assignment_email.delay(subject, message, obj.created_by.user.email)

admin.site.register(ProjectDocuments)
@admin.register(Tasks)
class TasksAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'project', 'assigned_to', 'status', 'priority', 'created_by', 'created_at', 'updated_at')
    list_filter = ('status', 'priority', 'project')
    search_fields = ('title', 'description', 'assigned_to__user__first_name', 'assigned_to__user__last_name')

admin.site.register(TaskComment)
admin.site.register(Folder)
admin.site.register(List)
admin.site.register(FolderFile)