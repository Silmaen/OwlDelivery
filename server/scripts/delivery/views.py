"""
Package views
"""

import re
import shutil
import tarfile
import zipfile
from base64 import b64decode
from pathlib import Path
from shutil import move

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt

from .api_pages import PAGE_ACTIONS
from .db_locking import locker
from .forms import NewsCommentForm, RevisionItemEntryFullForm
from .models import BranchEntry, NewsEntry, RevisionItemEntry
from .perms_utils import (
    can_see_admin,
    can_see_news_admin,
    can_see_pages_admin,
    can_see_revision_admin,
    can_see_stats_admin,
    is_comment_moderator,
)
from .release_utils import (
    branch_sort_key,
    get_latest_release,
    get_latest_release_branch,
    get_packages,
    get_release_note,
)
from .revision_utils import (
    find_revision,
    get_branch_documentation_url,
    get_revision_date,
    get_revision_hashes,
    get_revision_info,
    get_revision_name_list,
)

root = Path(__file__).resolve().parent.parent.parent
with open(root / "VERSION") as fp:
    lines = fp.readlines()
SITE_VERSION = lines[0].strip()
SITE_HASH = lines[1].strip()
STAFF_ACTIVE = settings.ENABLE_STAFF

# The API fields that end up in a path on disk. No segment may start with a dot, so `..` never passes.
PATH_SEGMENT = r"[A-Za-z0-9][A-Za-z0-9._+-]*"
SAFE_PATH_FIELDS = {
    "branch": re.compile(rf"^{PATH_SEGMENT}(/{PATH_SEGMENT})*$"),
    "hash": re.compile(rf"^{PATH_SEGMENT}$"),
    "package.name": re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+ ()-]*$"),
}
DOC_ARCHIVE_SUFFIXES = (".zip", ".tgz")
NEWS_PER_PAGE = 10


def news(request):
    """
    The news, newest first, `NEWS_PER_PAGE` per page.
    :param request: the page request
    :return: the rendered page
    """
    paginator = Paginator(NewsEntry.objects.filter(published=True).order_by("-date"), NEWS_PER_PAGE)
    news_page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "delivery/news.html",
        {
            "page": "news",
            "has_menu": True,
            "has_submenu": False,
            "news_page": news_page,
            "news_list": news_page.object_list,
            "staff_active": STAFF_ACTIVE,
            "is_admin": can_see_admin(request),
            "version": {"number": SITE_VERSION, "hash": SITE_HASH},
        },
    )


def news_details(request, news_id):
    """
    page for one article with details
    :param request: the page request
    :param news_id: the id of the article to find
    :return: the rendered page
    """
    news_item = get_object_or_404(NewsEntry, pk=news_id)
    if not news_item.published and not can_see_news_admin(request):
        raise Http404("No such news.")
    new_comment = None
    # comment posted (only for authenticated users)
    if request.method == "POST" and request.user.is_authenticated:
        comment_form = NewsCommentForm(data=request.POST)
        if comment_form.is_valid():
            # create an object but don't save to database yet
            new_comment = comment_form.save(commit=False)
            # assign the comment to the current Article
            new_comment.related_news = news_item
            # assign the current user to the comment
            new_comment.author = request.user
            # mark it as active if the user is in Moderators group
            new_comment.active = is_comment_moderator(request)
            # save it to database
            new_comment.save()
    else:
        comment_form = NewsCommentForm()
    published = NewsEntry.objects.filter(published=True)
    return render(
        request,
        "delivery/news_detail.html",
        {
            "page": "news",
            "has_menu": True,
            "has_submenu": False,
            "news_item": news_item,
            "comments": news_item.get_all_active_comments(),
            "newer": published.filter(date__gt=news_item.date).order_by("date").first(),
            "older": published.filter(date__lt=news_item.date).order_by("-date").first(),
            "comment_form": comment_form,
            "new_comment": new_comment,
            "staff_active": STAFF_ACTIVE,
            "is_admin": can_see_admin(request),
            "version": {"number": SITE_VERSION, "hash": SITE_HASH},
        },
    )


def branch_summary(branch):
    """
    One branch of the downloads page: name, newest revision, docs.
    """
    hashes = get_revision_hashes(branch.name)
    return {
        "name": branch.name,
        "stable": branch.stable,
        "date": get_revision_date(hashes[0]) if hashes else branch.date,
        "hash": hashes[0] if hashes else "",
        "revision_count": len(hashes),
        "doc_url": get_branch_documentation_url(branch.name),
    }


def branches(request):
    """
    The downloads: the latest release first (highest stable version, as on the presentation page), then the
    development branches and the older releases, newest version first.
    """
    visible = sorted(BranchEntry.objects.filter(visible=True), key=branch_sort_key, reverse=True)
    latest_branch = get_latest_release_branch()
    latest = None
    if latest_branch is not None:
        latest = get_latest_release()
        latest["summary"] = branch_summary(latest_branch)
    others = [branch for branch in visible if latest_branch is None or branch.pk != latest_branch.pk]
    return render(
        request,
        "delivery/branches.html",
        {
            "page": "revisions",
            "has_menu": True,
            "has_submenu": False,
            "staff_active": STAFF_ACTIVE,
            "is_admin": can_see_admin(request),
            "latest": latest,
            "dev_branch_list": [branch_summary(branch) for branch in others if not branch.stable],
            "old_stable_branch_list": [branch_summary(branch) for branch in others if branch.stable],
            "version": {"number": SITE_VERSION, "hash": SITE_HASH},
        },
    )


def revisions(request, rev_branch: str):
    """
    One branch: the downloads of its newest revision, then the older revisions.
    """
    branch = get_object_or_404(BranchEntry, name=rev_branch, visible=True)
    hashes = get_revision_hashes(rev_branch)
    current_revision = None
    if hashes:
        current_revision = {
            "hash": hashes[0],
            "date": get_revision_date(hashes[0]),
            "packages": get_packages(hashes[0]),
        }
    older_revisions = [
        {"hash": rev_hash, "date": get_revision_date(rev_hash), "names": get_revision_name_list(rev_hash)}
        for rev_hash in hashes[1:]
    ]
    return render(
        request,
        "delivery/revisions.html",
        {
            "page": "revisions",
            "has_menu": True,
            "has_submenu": False,
            "staff_active": STAFF_ACTIVE,
            "is_admin": can_see_admin(request),
            "branch": branch,
            "doc_url": get_branch_documentation_url(rev_branch),
            "release_note": get_release_note(rev_branch),
            "current_revision": current_revision,
            "older_revisions": older_revisions,
            "version": {"number": SITE_VERSION, "hash": SITE_HASH},
        },
    )


def revision_detail(request, rev_hash):
    """
    The files of one revision.
    """
    current_revision = get_revision_info(rev_hash)
    if not current_revision:
        raise Http404("No such revision.")
    hashes = get_revision_hashes(current_revision["branch"])
    return render(
        request,
        "delivery/revision_detail.html",
        {
            "page": "revisions",
            "has_menu": True,
            "has_submenu": False,
            "staff_active": STAFF_ACTIVE,
            "is_admin": can_see_admin(request),
            "revision": current_revision,
            "packages": get_packages(rev_hash),
            "is_newest": bool(hashes) and hashes[0] == rev_hash,
            "doc_url": get_branch_documentation_url(current_revision["branch"]),
            "version": {"number": SITE_VERSION, "hash": SITE_HASH},
        },
    )


def admin(request):
    """

    :param request:
    :return:
    """
    if not can_see_admin(request):
        return redirect("/")
    if can_see_news_admin(request):
        return redirect("a_news")
    if can_see_pages_admin(request):
        return redirect("a_pages")
    if can_see_revision_admin(request):
        return redirect("a_revisions")
    if can_see_stats_admin(request):
        return redirect("a_stats")
    return redirect("a_users")


def dl_script(request):
    file = Path(settings.STATICFILES_DIRS[0]) / "scripts" / "api.py"
    response = FileResponse(open(file, "rb"))
    response["Content-Disposition"] = 'attachment; filename="api.py"'
    return response


def find_unsafe_field(data):
    """
    :param data: The POST fields of an API request.
    :return: The name of the first field that cannot be used in a path, or None.
    """
    for field, pattern in SAFE_PATH_FIELDS.items():
        if field in data and not pattern.match(data[field]):
            return field
    return None


def is_spooled_upload(path_text):
    """
    `package.path` is set by the nginx upload module; a client can post it too, so it must point into the spool.
    :param path_text: The posted path.
    :return: True for an existing file under `MEDIA_ROOT/_upload`.
    """
    spool = (Path(settings.MEDIA_ROOT) / "_upload").resolve()
    path = Path(path_text).resolve()
    return path.is_file() and path.is_relative_to(spool)


def entry_exists(request, data):
    file_name = ""
    if len(request.FILES.dict()) > 0:
        file_name = next(iter(request.FILES.dict()))
    elif "package.path" in data:
        file_name = data["package.name"]
    new_path = Path(settings.MEDIA_ROOT) / "packages" / data["branch"] / data["hash"] / file_name
    if new_path.exists():
        return True
    return (
        RevisionItemEntry.objects.filter(
            hash=data["hash"],
            branch=data["branch"],
            name=data["name"],
            flavor_name=data["flavor_name"],
            rev_type=data["rev_type"],
        ).count()
        > 0
    )


@csrf_exempt
def revision_api(request):
    try:
        if not request.user.is_authenticated:
            if "Authorization" in request.headers:
                try:
                    key, dec = b64decode(request.headers["Authorization"].split()[-1]).decode("ascii").split(":", 1)
                    user = authenticate(request, username=key, password=dec)
                    if user is None:
                        return HttpResponseForbidden("Invalid credentials.")
                    # For this request only: a CI call must not create a session in the database.
                    request.user = user
                except Exception:
                    return HttpResponseForbidden("Invalid credentials.")
            if not request.user.is_authenticated:
                return HttpResponseForbidden("""Only authenticated user allowed""")
        if locker.is_locked():
            return HttpResponse("ERROR: Server is under maintenance, try again later.", status=406)
        if request.method == "GET":
            # if get method, simply DL the api script
            return dl_script(request)
        if request.method != "POST":
            return HttpResponse(
                f"ERROR invalid action.\nMETHOD: {request.method}",
                status=406,
            )
        data = request.POST.dict()
        if "package.path" in data:
            # Through the nginx upload module the text fields of the form are dropped: the client also sends them
            # in the query string, which `upload_pass_args` forwards. The body wins when both carry a field.
            data = {**request.GET.dict(), **data}
        if "action" not in data:
            return HttpResponse(
                f"ERROR no asked action.\nPOST: {data}",
                status=406,
            )
        action = data["action"]
        unsafe_field = find_unsafe_field(data)
        if unsafe_field is not None:
            return HttpResponse(f"ERROR invalid {unsafe_field} field.", status=406)
        if "package.path" in data and not is_spooled_upload(data["package.path"]):
            return HttpResponse("ERROR package.path is not an uploaded file.", status=406)
        if action == "version":
            return HttpResponse(f"version: {SITE_VERSION}\n", status=200)
        elif action in PAGE_ACTIONS:
            return PAGE_ACTIONS[action](request, data)
        elif action == "pull":
            return HttpResponse("""ERROR PULL function is not yet implemented.""", status=406)
        elif action == "push":
            if not request.user.has_perm("delivery.add_revisionitementry"):
                return HttpResponseForbidden("Insufficient permissions to upload packages.")
            try:
                if len(request.FILES.dict()) > 0:
                    form = RevisionItemEntryFullForm(request.POST, request.FILES)
                    if form.is_valid():
                        if entry_exists(request, data):
                            return HttpResponse(
                                "WARNING: Entry already exists.",
                                status=201,
                            )
                        form.save()
                        return HttpResponse(
                            f"GOOD.\nPOST: {data}\nFILES: {request.FILES.dict()}",
                            status=200,
                        )
                    else:
                        form.full_clean()
                        return HttpResponse(
                            f"INVALID FORM.\nPOST: {data}\nFILES: {request.FILES.dict()}",
                            status=406,
                        )
                elif "package.path" in data:
                    # temp file to destination folder
                    missing = []
                    ok = True
                    for d in [
                        "hash",
                        "branch",
                        "name",
                        "flavor_name",
                        "rev_type",
                        "date",
                    ]:
                        if d not in data.keys():
                            ok = False
                            missing.append(d)
                    if not ok:
                        return HttpResponse(
                            f"ERROR INVALID REQUEST.\nPOST: {data}\nERROR  Missing data: {missing}\n",
                            status=406,
                        )
                    origin_path = Path(data["package.path"])
                    new_path = (
                        Path(settings.MEDIA_ROOT) / "packages" / data["branch"] / data["hash"] / data["package.name"]
                    )
                    if entry_exists(request, data):
                        return HttpResponse(
                            "WARNING: Entry already exists.",
                            status=201,
                        )
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    move(origin_path, new_path)
                    # The spool is written world-writable (upload_store_access); a published package is not.
                    new_path.chmod(0o644)
                    RevisionItemEntry.objects.create(
                        hash=data["hash"],
                        branch=data["branch"],
                        name=data["name"],
                        flavor_name=data["flavor_name"],
                        rev_type=data["rev_type"],
                        date=data["date"],
                        package=str(new_path.relative_to(settings.MEDIA_ROOT)),
                    )
                    return HttpResponse(
                        f"GOOD.\nPOST: {data}",
                        status=200,
                    )
                else:
                    return HttpResponse(
                        f"ERROR  INVALID REQUEST.\nPOST: {data}\nERROR NO FILE",
                        status=406,
                    )
            except Exception as err:
                return HttpResponse(
                    f"ERROR problem with the data: {err}.\nPOST: {data}\nFILES: {request.FILES.dict()}\n",
                    status=406,
                )
        elif action == "push_doc":
            if not request.user.has_perm("delivery.add_revisionitementry"):
                return HttpResponseForbidden("Insufficient permissions to upload packages.")
            try:
                if "branch" not in data:
                    return HttpResponse(
                        f"ERROR INVALID REQUEST.\nPOST: {data}\nERROR  Missing branch field\n",
                        status=406,
                    )
                # Determine file origin: Nginx upload module (already checked to be in the spool) or direct upload
                if "package.path" in data:
                    origin_path = Path(data["package.path"])
                    origin_name = Path(data.get("package.name", origin_path.name))
                elif "package" in request.FILES:
                    uploaded = request.FILES["package"]
                    origin_name = Path(uploaded.name)
                    if not SAFE_PATH_FIELDS["package.name"].match(origin_name.name):
                        return HttpResponse("ERROR invalid package file name.", status=406)
                    upload_dir = Path(settings.MEDIA_ROOT) / "_upload"
                    upload_dir.mkdir(parents=True, exist_ok=True)
                    origin_path = upload_dir / origin_name.name
                    with open(origin_path, "wb") as f:
                        for chunk in uploaded.chunks():
                            f.write(chunk)
                else:
                    return HttpResponse(
                        f"ERROR  INVALID REQUEST.\nPOST: {data}\nERROR NO FILE in package field.\n",
                        status=406,
                    )
                try:
                    suffix = origin_name.suffix
                    # Checked before anything is removed: a wrong archive must not wipe the current docs.
                    if suffix not in DOC_ARCHIVE_SUFFIXES:
                        return HttpResponse(
                            f"ERROR  INVALID REQUEST.\nPOST: {data}\n"
                            f"ERROR FILE {origin_name} Format not supported {suffix}.\n",
                            status=406,
                        )
                    new_path = Path(settings.MEDIA_ROOT) / "documentation" / data["branch"]
                    if new_path.exists():
                        if not new_path.is_dir():
                            new_path.unlink(missing_ok=True)
                        else:
                            shutil.rmtree(new_path, ignore_errors=True)
                    new_path.mkdir(parents=True)
                    if suffix == ".zip":
                        with zipfile.ZipFile(origin_path, "r") as zip_ref:
                            zip_ref.extractall(new_path)
                    else:
                        with tarfile.open(origin_path, "r:gz") as tar_ref:
                            tar_ref.extractall(new_path, filter="data")
                finally:
                    # The archive is extracted (or refused): the spooled copy is no longer needed.
                    origin_path.unlink(missing_ok=True)
                return HttpResponse(
                    f"GOOD.\nPOST: {data}",
                    status=200,
                )
            except Exception as err:
                return HttpResponse(
                    f"ERROR problem with the data: {err}.\nPOST: {data}\nFILES: {request.FILES.dict()}\n",
                    status=406,
                )
        elif action == "delete":
            if not request.user.has_perm("delivery.delete_revisionitementry"):
                return HttpResponseForbidden("Please ask the right to delete packages")
            objs = find_revision(data)
            if len(objs) == 0:
                return HttpResponse("""ERROR No matching package.""", status=406)
            if len(objs) > 1:
                return HttpResponse("""ERROR more than one package match the query.""", status=406)
            objs[0].delete()
            return HttpResponse("GOOD. Deleted.", status=200)
        else:
            return HttpResponse(
                f"ERROR invalid action.\nPOST: {data}",
                status=406,
            )
    except Exception as err:
        return HttpResponse(f"""ERROR Exception during treatment {err}.""", status=406)
