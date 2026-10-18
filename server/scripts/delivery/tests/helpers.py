"""
Shared helpers of the delivery tests.
"""

import shutil
import tempfile
from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image


def png_bytes(width=1280, height=720, color=(190, 133, 9)):
    """
    A PNG image in memory.
    """
    buffer = BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, "PNG")
    return buffer.getvalue()


def png_upload(name="shot.png", width=1280, height=720, color=(190, 133, 9)):
    return SimpleUploadedFile(name, png_bytes(width, height, color), content_type="image/png")


class MediaTestCase(TestCase):
    """
    Test case writing its media files in a temporary folder of its own, per test.
    """

    def setUp(self):
        super().setUp()
        self.media_root = tempfile.mkdtemp(prefix="owl_media_")
        media_override = override_settings(MEDIA_ROOT=self.media_root)
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, True)


def make_item(branch, revision_hash, name="Owl Engine", flavor="linux glibc_2.43 x64", stable=None, with_file=True):
    """
    A revision item pushed like the engine CI does, its archive written under MEDIA_ROOT.
    """
    from django.conf import settings

    from delivery.models import BranchEntry, RevisionItemEntry

    relative = f"packages/{branch}/{revision_hash}/{name.replace(' ', '_')}-{flavor.replace(' ', '_')}.zip"
    if with_file:
        path = Path(settings.MEDIA_ROOT) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * 2048)
    item = RevisionItemEntry.objects.create(
        hash=revision_hash,
        branch=branch,
        name=name,
        flavor_name=flavor,
        rev_type="e" if name == "Owl Engine" else "a",
        package=relative,
    )
    if stable is not None:
        BranchEntry.objects.filter(name=branch).update(stable=stable)
    return item


class PagesTestCase(MediaTestCase):
    """
    Test case of the public pages: empty block cache, helpers for an editor of the pages.
    """

    def setUp(self):
        super().setUp()
        from django.core.cache import cache

        # The test database rolls back, the counter with it: cached blocks of another test would match.
        cache.clear()

    def make_editor(self, username="editor"):
        from django.contrib.auth.models import Permission, User

        user = User.objects.create_user(username, password="secret-password")
        user.user_permissions.add(Permission.objects.get(codename="change_featurecard"))
        return user
