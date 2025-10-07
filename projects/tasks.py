from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from .models import Tasks, Project
from employee.models import Employee

@shared_task
def send_task_created_email(task_id):
    """
    Send email notification when a task is created.
    """
    try:
        task = Tasks.objects.get(id=task_id)
        if task.assigned_to and task.assigned_to.user.email:
            subject = f"New Task Assigned: {task.title}"
            message = f"Hi {task.assigned_to.user.first_name},\n\n" \
                      f"You have been assigned a new task: {task.title}.\n" \
                      f"Project: {task.project.name}\n" \
                      f"Deadline: {task.due_date}\n\nBest,\nProject Management System"
            send_mail(subject, message, 'no-reply@projectsystem.com', [task.assigned_to.user.email])
            print(f"✅ Email sent successfully for task {task.title} to {task.assigned_to.user.email}")
        else:
            print(f"⚠️ Task {task.title} has no assigned employee with an email.")
    except Tasks.DoesNotExist:
        print(f"❌ Task with ID {task_id} not found.")

@shared_task
def send_project_created_email(project_id):
    """
    Send email notification to PM/TL/HR when a project is created.
    """
    try:
        project = Project.objects.get(id=project_id)
        recipients = []

        # Project Manager
        if project.manager and project.manager.user.email:
            recipients.append(project.manager.user.email)
        # Team Lead
        if project.team_lead and project.team_lead.user.email:
            recipients.append(project.team_lead.user.email)
        # HR/Admin members
        hr_members = Employee.objects.filter(role__in=["HR", "ADMIN"])
        recipients += [emp.user.email for emp in hr_members if emp.user.email]

        # Remove duplicates
        recipients = list(set(recipients))

        for email in recipients:
            subject = f"New Project Assigned: {project.name}"
            message = f"Hi,\n\nYou have been assigned or responsible for a new project: {project.name}.\n" \
                      f"Description: {project.description}\n" \
                      f"Start: {project.start_date}, End: {project.end_date}\n\nBest,\nProject Management System"
            send_mail(subject, message, 'no-reply@projectsystem.com', [email])
            print(f"✅ Email sent for project {project.name} to {email}")

    except Project.DoesNotExist:
        print(f"❌ Project with ID {project_id} not found.")

@shared_task
def check_overdue_tasks():
    """
    Periodically check and mark tasks as overdue and notify the assigned employee.
    """
    now = timezone.now()
    overdue_tasks = Tasks.objects.filter(due_date__lt=now, status__in=["pending", "in_progress"])
    
    for task in overdue_tasks:
        task.status = "overdue"
        task.save()
        if task.assigned_to and task.assigned_to.user.email:
            subject = f"Task Overdue: {task.title}"
            message = f"Hi {task.assigned_to.user.first_name},\n\n" \
                      f"The task assigned to you is now overdue: {task.title}.\n" \
                      f"Project: {task.project.name}\n" \
                      f"Original Deadline: {task.due_date}\n\nPlease take immediate action!\n\nBest,\nProject Management System"
            send_mail(subject, message, 'no-reply@projectsystem.com', [task.assigned_to.user.email])
            print(f"⚠️ Overdue email sent for task {task.title} to {task.assigned_to.user.email}")

    print(f"⚠️ {overdue_tasks.count()} task(s) marked as overdue.")
