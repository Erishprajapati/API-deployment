# project/urls.py
from rest_framework_nested import routers
from django.urls import path, include
from .views import *

# Base router for projects
router = routers.DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')

# Nested router for tasks under projects
projects_router = routers.NestedDefaultRouter(router, r'projects', lookup='project')
projects_router.register(r'tasks', TaskViewSet, basename='project-tasks')
projects_router.register(r'comments', TaskCommentViewSet, basename = "task-comments")
projects_router.register(r'folders', FolderViewSet, basename='folder')
projects_router.register(r'list', ListViewSet, basename='list')
projects_router.register(r'folder-files', FolderFileViewSet, basename='folderfile')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(projects_router.urls)),
]