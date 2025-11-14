from django.shortcuts import render
from rest_framework.views import APIView
from authentication.services.token_service import TokenService
from .serializers import LoginSerializer
from .exceptions import * 
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from authentication.services.user_service import AuthenticateService
from django.conf import settings
from employee.permissions import *
from datetime import datetime, timezone
from .serializers import *
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

User = get_user_model()
class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create user + employee
        employee = serializer.save()
        user = employee.user  # link created in serializer

        # Optional: Give staff rights so user can log into admin panel
        # user.is_staff = True
        # user.save()

        # Generate JWT tokens for immediate login
        tokens = TokenService.generate_token_for_user(user)

        return Response({
            "message": "Signup successful",
            "user_id": user.id,
            "employee_id": employee.id,
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "role": employee.role,
        }, status=status.HTTP_201_CREATED)

# class RefreshTokenView(APIView):
#     permission_classes = [IsNotAuthenticatedUser]
    

#     def post(self, request):
#         old_refresh_token = request.data.get("refresh_token")
#         if not old_refresh_token:
#             return Response(
#                 {"error": "Refresh token is required"},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         try:
#             old_token = RefreshToken(old_refresh_token)
#             user_id = old_token.payload.get("user_id")
#             user = User.objects.get(id=user_id, is_active=True)
#             new_refresh = RefreshToken.for_user(user)
#             new_access_token = str(new_refresh.access_token)
#             new_refresh_token = str(new_refresh)
#             new_refresh_exp = datetime.fromtimestamp(
#                 new_refresh.payload["exp"], tz=timezone.utc
#             )
#             secure_cookie = not settings.DEBUG
#             response = Response(
#                 {
#                     "message": "Access token refreshed",
#                     "refresh_token": new_refresh_token,
#                     "refresh_token_exp": new_refresh_exp.isoformat(),
#                 }
#             )

#             # Set new access token cookie
#             response.set_cookie(
#                 key="access_token",
#                 value=new_access_token,
#                 httponly=True,
#                 secure=False,
#                 samesite=None,
#                 max_age=900,  # 15 minutes
#             )

#             # Invalidate old refresh token
#             old_token.blacklist()

#             return response

#         except TokenError:
#             return Response(
#                 {"error": "Invalid or expired refresh token"},
#                 status=status.HTTP_401_UNAUTHORIZED,
#             )
#         except User.DoesNotExist:
#             return Response(
#                 {"error": "User account not found or disabled"},
#                 status=status.HTTP_401_UNAUTHORIZED,
#             )
class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": f"Hello, {request.user.username}!"})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def social_login_success(request):
    user = request.user
    return Response({
        "message": "Social login successful",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.get_full_name(),
        }
    })

class LoginView(APIView):
    permission_classes = [AllowAny]  # anyone can log in

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        # Authenticate user
        try:
            user = AuthenticateService.authenticate_user(request, email, password)
        except InvalidCredentialException:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        except InactiveException:
            return Response({"error": "Check your email inbox for activation link"}, status=status.HTTP_403_FORBIDDEN)

        # Generate tokens
        tokens = TokenService.generate_token_for_user(user)

        # Return response with role from employee_profile
        role = getattr(user.employee_profile, 'role', None)

        return Response({
            "message": "Login successful",
            "user_id": user.id,
            "access_token": tokens['access_token'],
            "refresh_token": tokens['refresh_token'],
            "role": role,
        }, status=status.HTTP_200_OK)