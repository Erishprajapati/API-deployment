from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import AccessToken


class CookieJWTAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="erish", password="password123")
        self.token = str(AccessToken.for_user(self.user))
        self.url = reverse("task-list")  # replace with your endpoint

    def test_auth_with_cookie(self):
        self.client.cookies["access_token"] = self.token
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_auth_with_header(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_no_token(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)
