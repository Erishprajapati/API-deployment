from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import *

app_name = "employee"

router = DefaultRouter()
router.register(r'employee-status', EmployeeStatusViewSet, basename='employee-status')
router.register(r'employee', EmployeeViewSet, basename='employee')
router.register(r'employee-profile', EmployeeProfileViewSet, basename='employee-profile')
router.register(r'department', DepartmentViewSet, basename='department')
router.register(r'leave', LeaveViewSet, basename='leave')
router.register(r'working-hour', WorkingHourViewSet, basename='working-hour')
router.register(r'employee-schedule', EmployeeScheduleViewSet, basename='employee-schedule')

urlpatterns = [
    path('', include(router.urls)),
]
