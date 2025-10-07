# authentication/urls.py
from django.urls import path, include
from .views import *
# from .views_google import GoogleAuthViewSet
from rest_framework.routers import DefaultRouter

app_name = "authentication"

# router = DefaultRouter()
# router.register(r'google', GoogleAuthViewSet, basename='google-auth')

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup_view"),
    path("login/", LoginView.as_view(), name="login_view"),
    path("logout/", LogoutView.as_view(), name="logout_view"),
    path("refresh-token/", RefreshTokenView.as_view(), name="refresh_token_view"),
    # path("protected-view/", ProtectedView.as_view(), name="protected_view"),

    # path("", include(router.urls)),
]
