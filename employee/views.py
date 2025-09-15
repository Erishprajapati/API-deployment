from rest_framework import viewsets, filters, status
from .models import *
from .serializers import * 
from .permissions import *
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from .filters import EmployeeFilter
from rest_framework_simplejwt.authentication import JWTAuthentication
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import JsonResponse
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from rest_framework.response import Response

class EmployeeStatusViewSet(viewsets.ModelViewSet):
    queryset = EmployeeStatus.objects.all()
    serializer_class = EmployeeStatusSerializer
    lookup_field = "id"
    http_method_names = ['get', 'post', 'put', 'patch']

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all().order_by('id')
    serializer_class = DepartmentSerializer
    lookup_field = 'id'
    permission_classes = [IsHRorSuperUser]
    http_method_names = ['get', 'post', 'put', 'patch']
    
class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all().order_by('id')
    serializer_class = EmployeeSerializer
    lookup_field = 'id'
    http_method_names = ['get', 'post', 'put', 'patch']
    permission_classes = [IsProjectManagerOrSuperUserOrHR]
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = EmployeeFilter
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'department__name', 'role', 'phone']
    ordering_fields = ['user__first_name', 'user__last_name', 'user__email', 'role']
    ordering = ['id']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = serializer.save()
        return Response({
            "message": "Employee created successfully!",
            "employee": EmployeeSerializer(employee).data
        }, status=status.HTTP_201_CREATED)
# class EmployeeProfileViewSet(viewsets.ModelViewSet):
#     queryset = EmployeeProfile.objects.all().order_by('id')
#     serializer_class = EmployeeProfileSerializer
#     lookup_field = 'id'
#     permission_classes = [IsSelfOrTeamLeadOrHROrPMOrADMIN]
#     http_method_names = ['get', 'post', 'put', 'patch']

#     """code ensures the employee can view their own profile"""
#     """HR, Team_lead, Project_manager can view all the profiles of employee"""
#     def get_queryset(self):
#         user = self.request.user  
#         if has_role(user, Employee.HR, Employee.TEAM_LEAD, Employee.ADMIN, Employee.PROJECT_MANAGER):
#             return EmployeeProfile.objects.all().order_by('id')
#         return EmployeeProfile.objects.filter(employee=user)
    
class EmployeeProfileViewSet(viewsets.ModelViewSet):
    queryset = EmployeeProfile.objects.all().order_by('id')
    serializer_class = EmployeeProfileSerializer
    lookup_field = 'id'
    http_method_names = ['get', 'post', 'put', 'patch']
    permission_classes = [IsSelfOrTeamLeadOrHROrPMOrADMIN]

    def get_queryset(self):
        user = self.request.user  

        # HR, PM, Admin, Team Lead → all profiles
        if has_role(user, Employee.HR, Employee.PROJECT_MANAGER, Employee.ADMIN, Employee.TEAM_LEAD):
            return EmployeeProfile.objects.all().order_by("id")

        # Normal employee → only their own profile
        return EmployeeProfile.objects.filter(employee__user=user)

class JWTSocialLoginView(SocialLoginView):
    client_class = OAuth2Client
    def get_response(self):
        user = self.user
        refresh = RefreshToken.for_user(user)
        return JsonResponse({
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.get_full_name() or user.username,
            }
        })
    
class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    callback_url = "http://localhost:8000/api/auth/google/callback/"

    # Return SimpleJWT tokens after successful social login
    def get_response(self):
        user = self.user
        refresh = RefreshToken.for_user(user)
        return JsonResponse({"access": str(refresh.access_token), "refresh": str(refresh)})
    

class LeaveViewSet(viewsets.ModelViewSet):
    queryset = Leave.objects.all()
    serializer_class = LeaveSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'patch']

class WorkingHourViewSet(viewsets.ModelViewSet):
    queryset = WorkingHour.objects.all()
    serializer_class = WorkinghourSerializer
    permission_classes = [IsAuthenticated]

class EmployeeScheduleViewSet(viewsets.ModelViewSet):
    queryset = EmployeeSchedule.objects.all()
    serializer_class = EmployeeScheduleSerializer
    permission_classes = [IsProjectManagerOrSuperUserOrHR]