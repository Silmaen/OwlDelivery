"""
Signals: cache invalidation of the pages, clean-up of the image and package files.
"""

from pathlib import Path

from django.conf import settings
from django.db.models.signals import post_delete, post_save

from .models import BranchEntry, NewsEntry, RevisionItemEntry
from .models_pages import PAGE_MODELS, ShowcaseImage, bump_content_version

# Every model whose rows show on the home or presentation page.
CONTENT_SENDERS = (*PAGE_MODELS, NewsEntry, BranchEntry, RevisionItemEntry)


def on_content_change(sender, instance, raw=False, **kwargs):
    """
    A row shown on a page changed: the cached blocks are stale.
    """
    if raw:
        return
    bump_content_version()


def on_image_delete(sender, instance, **kwargs):
    """
    Remove the files of a deleted showcase image.
    """
    for field_file in (instance.image, instance.thumbnail):
        if field_file:
            field_file.storage.delete(field_file.name)


def on_package_delete(sender, instance, **kwargs):
    """
    Remove the archive of a deleted revision item, and the folders it leaves empty under `packages/`:
    a deleted package must not stay downloadable from its URL.
    """
    if not instance.package:
        return
    path = Path(instance.package.path)
    path.unlink(missing_ok=True)
    packages_root = Path(settings.MEDIA_ROOT) / "packages"
    folder = path.parent
    while (
        folder != packages_root
        and folder.is_relative_to(packages_root)
        and folder.is_dir()
        and not any(folder.iterdir())
    ):
        folder.rmdir()
        folder = folder.parent


def connect():
    for sender in CONTENT_SENDERS:
        post_save.connect(on_content_change, sender=sender, dispatch_uid=f"pages_save_{sender.__name__}")
        post_delete.connect(on_content_change, sender=sender, dispatch_uid=f"pages_delete_{sender.__name__}")
    post_delete.connect(on_image_delete, sender=ShowcaseImage, dispatch_uid="pages_image_files")
    post_delete.connect(on_package_delete, sender=RevisionItemEntry, dispatch_uid="package_files")
