"""
The /api fields that become paths on disk cannot leave their folder.
"""

import io
import zipfile
from base64 import b64encode
from pathlib import Path

from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile

from delivery.models import RevisionItemEntry

from .helpers import MediaTestCase

AUTH = {"HTTP_AUTHORIZATION": "Basic " + b64encode(b"ci:ci-password").decode()}
PACKAGE_FIELDS = {
    "action": "push",
    "hash": "aaa111",
    "branch": "0.3.0",
    "name": "Owl Engine",
    "flavor_name": "linux x64",
    "date": "2026-10-11 12:00",
    "rev_type": "e",
}


def doc_archive(name="doc.zip"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("index.html", "<html></html>")
    return SimpleUploadedFile(name, buffer.getvalue())


class ApiPathsTest(MediaTestCase):
    def setUp(self):
        super().setUp()
        ci = User.objects.create_user("ci", password="ci-password")
        ci.user_permissions.add(Permission.objects.get(codename="add_revisionitementry"))
        self.media = Path(self.media_root)
        self.sentinel = self.media / "delivery.db"
        self.sentinel.write_text("the database")

    def post(self, data):
        return self.client.post("/api", data, **AUTH)

    def spooled(self, content=b"archive"):
        path = self.media / "_upload" / "3" / "0000000003"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_push_doc_branch_cannot_climb(self):
        for branch in ("..", "../escaped", "a/../../escaped", "/abs"):
            response = self.post({"action": "push_doc", "branch": branch, "package": doc_archive()})
            self.assertEqual(response.status_code, 406, branch)
        self.assertEqual(self.sentinel.read_text(), "the database")
        self.assertFalse((self.media / "escaped").exists())

    def test_push_doc_still_works(self):
        response = self.post({"action": "push_doc", "branch": "0.3.0", "package": doc_archive()})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue((self.media / "documentation" / "0.3.0" / "index.html").exists())
        self.assertEqual(list((self.media / "_upload").iterdir()), [])

    def test_wrong_archive_keeps_the_current_docs(self):
        self.post({"action": "push_doc", "branch": "0.3.0", "package": doc_archive()})
        response = self.post({"action": "push_doc", "branch": "0.3.0", "package": doc_archive("doc.rar")})
        self.assertEqual(response.status_code, 406)
        self.assertTrue((self.media / "documentation" / "0.3.0" / "index.html").exists())

    def test_package_path_must_be_in_the_spool(self):
        data = {**PACKAGE_FIELDS, "package.path": str(self.sentinel), "package.name": "db.zip"}
        response = self.post(data)
        self.assertEqual(response.status_code, 406)
        self.assertEqual(self.sentinel.read_text(), "the database")
        self.assertFalse(RevisionItemEntry.objects.exists())
        response = self.post({"action": "push_doc", "branch": "0.3.0", "package.path": str(self.sentinel)})
        self.assertEqual(response.status_code, 406)
        self.assertTrue(self.sentinel.exists())

    def test_spooled_upload_is_moved(self):
        spooled = self.spooled()
        response = self.post({**PACKAGE_FIELDS, "package.path": str(spooled), "package.name": "Owl-linux-x64.zip"})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(spooled.exists())
        self.assertTrue((self.media / "packages" / "0.3.0" / "aaa111" / "Owl-linux-x64.zip").exists())

    def test_hash_and_file_name_cannot_climb(self):
        spooled = self.spooled()
        for field, value in (("hash", "../../x"), ("package.name", "../../delivery.db"), ("branch", "../x")):
            data = {**PACKAGE_FIELDS, "package.path": str(spooled), "package.name": "ok.zip", field: value}
            self.assertEqual(self.post(data).status_code, 406, field)
        self.assertTrue(spooled.exists())
        self.assertEqual(self.sentinel.read_text(), "the database")

    def test_fields_in_the_query_string_of_an_nginx_upload(self):
        spooled = self.spooled()
        fields = {k: v for k, v in PACKAGE_FIELDS.items()}
        query = "&".join(f"{k}={v.replace(' ', '%20')}" for k, v in fields.items())
        body = {"package.path": str(spooled), "package.name": "Owl-linux-x64.zip"}
        response = self.client.post(f"/api?{query}", body, **AUTH)
        self.assertEqual(response.status_code, 200, response.content)
        target = self.media / "packages" / "0.3.0" / "aaa111" / "Owl-linux-x64.zip"
        self.assertEqual(target.stat().st_mode & 0o777, 0o644)

    def test_query_string_is_ignored_without_an_nginx_upload(self):
        response = self.client.post("/api?action=push", {}, **AUTH)
        self.assertEqual(response.status_code, 406)
        self.assertIn(b"no asked action", response.content)

    def test_query_string_fields_are_validated_too(self):
        spooled = self.spooled()
        body = {"package.path": str(spooled), "package.name": "ok.zip"}
        response = self.client.post("/api?action=push_doc&branch=..", body, **AUTH)
        self.assertEqual(response.status_code, 406)
        self.assertEqual(self.sentinel.read_text(), "the database")
