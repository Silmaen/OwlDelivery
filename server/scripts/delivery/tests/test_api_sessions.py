"""
HTTP Basic calls of the CI do not open sessions.
"""

from base64 import b64encode

from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.test import TestCase


class ApiSessionTest(TestCase):
    def test_basic_auth_creates_no_session(self):
        User.objects.create_user("ci", password="ci-password")
        auth = "Basic " + b64encode(b"ci:ci-password").decode()
        for _ in range(3):
            response = self.client.post("/api", {"action": "version"}, HTTP_AUTHORIZATION=auth)
            self.assertEqual(response.status_code, 200)
        self.assertEqual(Session.objects.count(), 0)

    def test_wrong_password_is_403(self):
        User.objects.create_user("ci", password="ci-password")
        auth = "Basic " + b64encode(b"ci:wrong").decode()
        self.assertEqual(self.client.post("/api", {"action": "version"}, HTTP_AUTHORIZATION=auth).status_code, 403)
