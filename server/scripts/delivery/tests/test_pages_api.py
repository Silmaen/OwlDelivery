"""
Tests of the API actions of the pages: `push_screenshot`, `push_release`, `release_info`.
"""

from base64 import b64encode
from datetime import date
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile

from delivery.models import RevisionItemEntry
from delivery.models_pages import ReleaseNote, ShowcaseImage, SiteSettings
from delivery.views_admin import PAGES_PUSH_CODENAMES

from .helpers import PagesTestCase, make_item, png_upload


class PagesApiTest(PagesTestCase):
    def setUp(self):
        super().setUp()
        self.ci = User.objects.create_user("ci", password="ci-password")
        self.ci.user_permissions.add(*Permission.objects.filter(codename__in=PAGES_PUSH_CODENAMES))
        self.auth = {"HTTP_AUTHORIZATION": "Basic " + b64encode(b"ci:ci-password").decode()}

    def post(self, data, **headers):
        return self.client.post("/api", data, **(headers or self.auth))

    def test_push_screenshot_creates_a_ci_draft(self):
        response = self.post(
            {"action": "push_screenshot", "key": "raycast", "caption": "E1M1", "package": png_upload()}
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn(b"created (draft)", response.content)
        image = ShowcaseImage.objects.get(key="raycast")
        self.assertEqual(image.source, "ci")
        self.assertFalse(image.published)
        self.assertEqual(image.alt_text, "E1M1")
        self.assertTrue(Path(image.thumbnail.path).exists())

    def test_second_push_replaces_the_image_and_keeps_admin_edits(self):
        self.post({"action": "push_screenshot", "key": "raycast", "caption": "CI caption", "package": png_upload()})
        image = ShowcaseImage.objects.get(key="raycast")
        image.caption = "Admin caption"
        image.published = True
        image.save()
        old_name = image.image.name
        response = self.post({"action": "push_screenshot", "key": "raycast", "package": png_upload(color=(1, 2, 3))})
        self.assertEqual(response.status_code, 200, response.content)
        image.refresh_from_db()
        self.assertEqual(image.caption, "Admin caption")
        self.assertTrue(image.published)
        self.assertNotEqual(image.image.name, old_name)

    def test_publish_flag_and_site_images(self):
        self.post({"action": "push_screenshot", "key": "hub", "publish": "true", "package": png_upload()})
        self.post(
            {"action": "push_screenshot", "key": "social_preview", "in_gallery": "false", "package": png_upload()}
        )
        self.assertTrue(ShowcaseImage.objects.get(key="hub").published)
        self.assertFalse(ShowcaseImage.objects.get(key="social_preview").in_gallery)
        settings_row = SiteSettings.load()
        self.assertEqual(settings_row.hero_image.key, "hub")
        self.assertEqual(settings_row.social_image.key, "social_preview")

    def test_missing_key_is_406(self):
        response = self.post({"action": "push_screenshot", "package": png_upload()})
        self.assertEqual(response.status_code, 406)

    def test_missing_file_on_a_new_key_is_406(self):
        self.assertEqual(self.post({"action": "push_screenshot", "key": "hub"}).status_code, 406)

    def test_not_an_image_is_406(self):
        bogus = SimpleUploadedFile("hub.png", b"not an image", content_type="image/png")
        self.assertEqual(self.post({"action": "push_screenshot", "key": "hub", "package": bogus}).status_code, 406)
        self.assertFalse(ShowcaseImage.objects.exists())

    def test_without_permission_is_403(self):
        User.objects.create_user("dev", password="dev-password")
        auth = {"HTTP_AUTHORIZATION": "Basic " + b64encode(b"dev:dev-password").decode()}
        response = self.post({"action": "push_screenshot", "key": "hub", "package": png_upload()}, **auth)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.post({"action": "push_release", "branch": "0.3.0"}, **auth).status_code, 403)

    def test_locked_server_is_406(self):
        with mock.patch("delivery.views.locker.is_locked", return_value=True):
            response = self.post({"action": "push_screenshot", "key": "hub", "package": png_upload()})
        self.assertEqual(response.status_code, 406)
        self.assertIn(b"maintenance", response.content)

    def test_push_release_upserts(self):
        response = self.post(
            {"action": "push_release", "branch": "0.3.0", "title": "Foundations", "release_date": "2026-10-11"}
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.post({"action": "push_release", "branch": "0.3.0", "changelog_url": "https://example.com/changelog"})
        note = ReleaseNote.objects.get(branch="0.3.0")
        self.assertEqual(note.title, "Foundations")
        self.assertEqual(note.release_date, date(2026, 10, 11))
        self.assertEqual(note.changelog_url, "https://example.com/changelog")
        self.assertEqual(ReleaseNote.objects.count(), 1)

    def test_push_release_rejects_bad_values(self):
        self.assertEqual(self.post({"action": "push_release"}).status_code, 406)
        bad_date = {"action": "push_release", "branch": "0.3.0", "release_date": "11/10"}
        self.assertEqual(self.post(bad_date).status_code, 406)
        self.assertEqual(
            self.post({"action": "push_release", "branch": "0.3.0", "changelog_url": "not a url"}).status_code, 406
        )

    def test_release_info(self):
        make_item("0.3.0", "aaa111", stable=True)
        response = self.post({"action": "release_info"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"release: 0.3.0", response.content)

    def test_existing_push_is_unchanged(self):
        self.ci.user_permissions.add(Permission.objects.get(codename="add_revisionitementry"))
        package = SimpleUploadedFile("OwlEngine-linux-x64.zip", b"zip content")
        response = self.post(
            {
                "action": "push",
                "hash": "aaa111",
                "branch": "0.3.0",
                "name": "Owl Engine",
                "flavor_name": "linux x64",
                "date": "2026-10-11 12:00",
                "rev_type": "e",
                "package": package,
            }
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(RevisionItemEntry.objects.filter(hash="aaa111").exists())

    def test_pushed_screenshot_reaches_the_seeded_sample(self):
        from delivery.models_pages import SampleGame
        from delivery.pages_seed import seed_pages

        seed_pages()
        self.post({"action": "push_screenshot", "key": "raycast", "package": png_upload()})
        self.assertEqual(SampleGame.objects.get(slug="wolfenstein").image.key, "raycast")
