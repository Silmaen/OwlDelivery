"""
API actions feeding the presentation page: `push_screenshot`, `push_release`, `release_info`.

Same conventions as the package actions of `views.revision_api`: plain-text answers, 200 when done, 403 without the
permission, 406 for an invalid request.
"""

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, URLValidator
from django.forms import ImageField
from django.http import HttpResponse, HttpResponseForbidden
from django.utils.dateparse import parse_date

from .models_pages import IMAGE_EXTENSIONS, STYLE_TAG_CHOICES, ReleaseNote, ShowcaseImage, validate_showcase_image
from .pages_seed import link_new_image
from .release_utils import release_info_text

# Screenshots go through the direct upload path, never the nginx upload module.
MAX_SCREENSHOT_BYTES = 100 * 1024 * 1024
TRUE_VALUES = ("1", "true", "yes", "on")
SCREENSHOT_TEXT_FIELDS = ("caption", "alt_text", "style_tag")
RELEASE_TEXT_FIELDS = ("title", "highlights", "changelog_url")


def is_true(value):
    return str(value).strip().lower() in TRUE_VALUES


def refuse(message):
    return HttpResponse(f"ERROR {message}", status=406)


def push_screenshot(request, data):
    """
    Create or update the showcase image of a key. A new image is a draft unless `publish` is true; on an existing
    one only the sent fields change, so the captions edited in the admin are kept.
    """
    if not request.user.has_perm("delivery.add_showcaseimage"):
        return HttpResponseForbidden("Insufficient permissions to push screenshots.")
    key = data.get("key", "").strip()
    if not key:
        return refuse("Missing key field.")
    if data.get("style_tag") and data["style_tag"] not in dict(STYLE_TAG_CHOICES):
        return refuse(f"Unknown style_tag {data['style_tag']}.")
    upload = request.FILES.get("package")
    image = ShowcaseImage.objects.filter(key=key).first()
    if image is None and upload is None:
        return refuse("No file in package field.")
    if upload is not None:
        if upload.size > MAX_SCREENSHOT_BYTES:
            return refuse("Screenshot larger than 100 MB.")
        try:
            ImageField(validators=[FileExtensionValidator(IMAGE_EXTENSIONS), validate_showcase_image]).clean(upload)
        except ValidationError as err:
            return refuse(f"Invalid image: {' '.join(err.messages)}")
    created = image is None
    if created:
        image = ShowcaseImage(
            key=key,
            source="ci",
            published=is_true(data.get("publish", "false")),
            alt_text=data.get("alt_text") or data.get("caption") or key,
        )
    elif "publish" in data:
        image.published = is_true(data["publish"])
    for field in SCREENSHOT_TEXT_FIELDS:
        if field in data:
            setattr(image, field, data[field])
    if "in_gallery" in data:
        image.in_gallery = is_true(data["in_gallery"])
    if upload is not None:
        image.image = upload
    try:
        image.full_clean()
    except ValidationError as err:
        return refuse(f"Invalid screenshot: {err.message_dict}")
    image.save()
    if created:
        link_new_image(image)
    state = "published" if image.published else "draft"
    return HttpResponse(f"GOOD. Screenshot {key} {'created' if created else 'updated'} ({state}).", status=200)


def push_release(request, data):
    """
    Create or update the release note of a branch. `BranchEntry.stable` is left to the maintainer.
    """
    if not request.user.has_perm("delivery.add_releasenote"):
        return HttpResponseForbidden("Insufficient permissions to push release notes.")
    branch = data.get("branch", "").strip()
    if not branch:
        return refuse("Missing branch field.")
    note = ReleaseNote.objects.filter(branch=branch).first()
    created = note is None
    if created:
        note = ReleaseNote(branch=branch)
    for field in RELEASE_TEXT_FIELDS:
        if field in data:
            setattr(note, field, data[field])
    if data.get("changelog_url"):
        try:
            URLValidator()(data["changelog_url"])
        except ValidationError:
            return refuse("Invalid changelog_url.")
    if "release_date" in data:
        release_date = parse_date(data["release_date"]) if data["release_date"] else None
        if data["release_date"] and release_date is None:
            return refuse("Invalid release_date, expected YYYY-MM-DD.")
        note.release_date = release_date
    note.save()
    return HttpResponse(f"GOOD. Release note {branch} {'created' if created else 'updated'}.", status=200)


def release_info(request, data):
    return HttpResponse(release_info_text(), status=200, content_type="text/plain")


PAGE_ACTIONS = {
    "push_screenshot": push_screenshot,
    "push_release": push_release,
    "release_info": release_info,
}
