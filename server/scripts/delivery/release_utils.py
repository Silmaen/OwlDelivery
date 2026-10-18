"""
The release offered by the pages, derived from the branches and their revisions.

`BranchEntry.date` moves with every push, so it never decides which release is the latest: the highest
`MAJOR.MINOR.PATCH` among the visible stable branches does.
"""

import logging
import re

from django.urls import reverse

from .models import BranchEntry
from .models_pages import ReleaseNote, SiteLink
from .revision_utils import get_branch_documentation_url, get_revision_date, get_revision_hashes, get_revision_info

logger = logging.getLogger(__name__)

VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
OS_LABELS = {"linux": "Linux", "windows": "Windows", "macos": "macOS", "darwin": "macOS"}
MISSING_SIZE = "(void)"


def parse_version(name):
    """
    :param name: A branch name such as `0.3.0` or `v1.0.0`.
    :return: The version as a tuple of integers, or None when the name is not a version.
    """
    match = VERSION_PATTERN.match(str(name).strip())
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def branch_sort_key(branch):
    """
    Versions first, highest last; names that are not versions before them, by date.
    """
    version = parse_version(branch.name)
    return version is not None, version or (), branch.date


def flavor_label(flavor_name):
    """
    Platform of an archive from its flavor words: `linux glibc_2.43 x64` → (`Linux x64`, `glibc_2.43`).
    :param flavor_name: The flavor name pushed by the engine CI.
    :return: The button label and the remaining detail words.
    """
    words = str(flavor_name).split()
    if not words:
        return "Download", ""
    system = OS_LABELS.get(words[0].lower(), words[0].capitalize())
    if len(words) == 1:
        return system, ""
    return f"{system} {words[-1]}", " ".join(words[1:-1])


def archive_format(url):
    """
    :param url: URL of a package file.
    :return: Its archive format (`zip`, `tar.gz`, ...), shown in the download button.
    """
    name = str(url).rsplit("/", 1)[-1].lower()
    for compound in (".tar.gz", ".tar.xz", ".tar.bz2"):
        if name.endswith(compound):
            return compound[1:]
    return name.rsplit(".", 1)[-1] if "." in name else ""


def get_latest_release_branch():
    """
    :return: The visible stable branch with the highest version, or None.
    """
    branches = list(BranchEntry.objects.filter(visible=True, stable=True))
    if not branches:
        return None
    return max(branches, key=branch_sort_key)


def get_release_note(branch_name, include_drafts=False):
    notes = ReleaseNote.objects.filter(branch=branch_name)
    if not include_drafts:
        notes = notes.filter(published=True)
    return notes.select_related("news").first()


def get_changelog_url(note):
    if note is not None and note.changelog_url:
        return note.changelog_url
    link = SiteLink.objects.filter(kind="changelog", published=True).exclude(url="").first()
    return link.url if link else ""


def get_packages(revision_hash):
    """
    Download buttons of one revision, grouped by package name.
    """
    packages = []
    for item in get_revision_info(revision_hash).get("item_list", []):
        flavors = []
        for flavor in item["flavors"]:
            label, detail = flavor_label(flavor["name"])
            if flavor["size"] == MISSING_SIZE:
                logger.warning("Package file missing on disk: %s (%s)", item["name"], flavor["url"])
            flavors.append({**flavor, "label": label, "detail": detail, "format": archive_format(flavor["url"])})
        flavors.sort(key=lambda flavor: flavor["label"])
        packages.append({"name": item["name"], "type": item["type"], "flavors": flavors})
    return packages


def get_latest_release(include_drafts=False):
    """
    :param include_drafts: Use an unpublished release note too (preview).
    :return: The release offered by the pages, or None when no stable branch is visible.
    """
    branch = get_latest_release_branch()
    if branch is None:
        return None
    hashes = get_revision_hashes(branch.name)
    note = get_release_note(branch.name, include_drafts)
    revision_hash = hashes[0] if hashes else ""
    build_date = get_revision_date(revision_hash) if revision_hash else None
    return {
        "version": branch.name,
        "hash": revision_hash,
        "date": note.release_date if note and note.release_date else build_date,
        "note": note,
        "packages": get_packages(revision_hash) if revision_hash else [],
        "doc_url": get_branch_documentation_url(branch.name) or "",
        "revisions_url": reverse("revisions", args=[branch.name]),
        "changelog_url": get_changelog_url(note),
    }


def get_dev_build(release=None):
    """
    :param release: The latest release, as returned by `get_latest_release`.
    :return: The newest visible development branch above the release, or None.
    """
    branches = list(BranchEntry.objects.filter(visible=True, stable=False))
    if release is not None:
        floor = parse_version(release["version"])
        branches = [
            branch
            for branch in branches
            if parse_version(branch.name) is not None and (floor is None or parse_version(branch.name) > floor)
        ]
    branches = [branch for branch in branches if get_revision_hashes(branch.name)]
    if not branches:
        return None
    branch = max(branches, key=branch_sort_key)
    revision_hash = get_revision_hashes(branch.name)[0]
    return {
        "version": branch.name,
        "hash": revision_hash,
        "date": get_revision_date(revision_hash),
        "url": reverse("revision_detail", args=[revision_hash]),
    }


def get_latest_docs_url():
    """
    :return: Documentation URL of the latest release, or an empty string.
    """
    branch = get_latest_release_branch()
    if branch is None:
        return ""
    return get_branch_documentation_url(branch.name) or ""


def release_info_text():
    """
    Plain-text dump of the derived release, for a CI check after publication.
    """
    release = get_latest_release()
    if release is None:
        return "release: none\n"
    lines = [f"release: {release['version']}", f"hash: {release['hash']}", f"date: {release['date']}"]
    for package in release["packages"]:
        for flavor in package["flavors"]:
            lines.append(f"package: {package['name']} | {flavor['name']} | {flavor['size']}")
    dev_build = get_dev_build(release)
    if dev_build is not None:
        lines.append(f"dev_build: {dev_build['version']} {dev_build['hash']}")
    return "\n".join(lines) + "\n"
