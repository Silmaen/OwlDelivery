"""
The /api answers must never echo the request headers: they carry the HTTP Basic credentials.
"""

from base64 import b64encode

from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile

from .helpers import MediaTestCase

CREDENTIALS = b64encode(b"ci:ci-password").decode()


class ApiResponsesTest(MediaTestCase):
    def setUp(self):
        super().setUp()
        ci = User.objects.create_user("ci", password="ci-password")
        ci.user_permissions.add(Permission.objects.get(codename="add_revisionitementry"))

    def post(self, data):
        response = self.client.post("/api", data, HTTP_AUTHORIZATION=f"Basic {CREDENTIALS}")
        content = response.content.decode()
        self.assertNotIn(CREDENTIALS, content)
        self.assertNotIn("Authorization", content)
        self.assertNotIn("headers:", content)
        return response

    def test_push_success(self):
        package = SimpleUploadedFile("OwlEngine-linux-x64.zip", b"zip content")
        data = {
            "action": "push",
            "hash": "aaa111",
            "branch": "0.3.0",
            "name": "Owl Engine",
            "flavor_name": "linux x64",
            "date": "2026-10-11 12:00",
            "rev_type": "e",
            "package": package,
        }
        response = self.post(data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("GOOD.", response.content.decode())

    def test_push_errors(self):
        self.assertEqual(self.post({"action": "push", "hash": "aaa111"}).status_code, 406)
        self.assertEqual(self.post({"action": "push", "package.path": "/tmp/x", "hash": "a"}).status_code, 406)
        self.assertEqual(self.post({"action": "push_doc"}).status_code, 406)
        self.assertEqual(self.post({"action": "push_doc", "branch": "0.3.0"}).status_code, 406)
        self.assertEqual(self.post({"action": "nope"}).status_code, 406)
        self.assertEqual(self.post({}).status_code, 406)

    def test_wrong_method(self):
        response = self.client.put("/api", HTTP_AUTHORIZATION=f"Basic {CREDENTIALS}")
        self.assertEqual(response.status_code, 406)
        self.assertNotIn(CREDENTIALS, response.content.decode())
