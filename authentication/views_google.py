# from rest_framework import viewsets, status
# from rest_framework.response import Response
# from django.contrib.auth.models import User
# from rest_framework.decorators import action
# from rest_framework_simplejwt.tokens import RefreshToken
# from google.oauth2 import id_token
# from google.auth.transport import requests

# class GoogleAuthViewSet(viewsets.ViewSet):
#     """
#     Handle Google OAuth login via POST request to /api/auth/google/login/
#     """

#     @action(detail=False, methods=['post'])
#     def login(self, request):
#         token = request.data.get("token")

#         if not token:
#             return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             # Verify token using Google
#             idinfo = id_token.verify_oauth2_token(
#                 token,
#                 requests.Request(),
#                 "990521328896-2jjfhf7ec5tcvutd7sb9ghdmuirujl04.apps.googleusercontent.com"
#             )

#             email = idinfo.get("email")
#             name = idinfo.get("name", "No Name")

#             # Create or get user
#             user, created = User.objects.get_or_create(
#                 username=email,
#                 defaults={"email": email, "first_name": name}
#             )

#             # Generate JWT tokens
#             refresh = RefreshToken.for_user(user)
#             data = {
#                 "refresh": str(refresh),
#                 "access": str(refresh.access_token),
#                 "email": user.email,
#                 "name": user.first_name,
#                 "is_new": created,
#             }

#             return Response(data, status=status.HTTP_200_OK)

#         except ValueError:
#             return Response({"error": "Invalid Google token"}, status=status.HTTP_400_BAD_REQUEST)

