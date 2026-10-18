"""
Signals of the page content: cache invalidation and image file clean-up.
"""

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


def connect():
    for sender in CONTENT_SENDERS:
        post_save.connect(on_content_change, sender=sender, dispatch_uid=f"pages_save_{sender.__name__}")
        post_delete.connect(on_content_change, sender=sender, dispatch_uid=f"pages_delete_{sender.__name__}")
    post_delete.connect(on_image_delete, sender=ShowcaseImage, dispatch_uid="pages_image_files")
