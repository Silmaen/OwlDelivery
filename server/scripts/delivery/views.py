"""
Package views
"""

import shutil
import tarfile
import zipfile
from base64 import b64decode
from shutil import move

from django.contrib.auth import authenticate, login
from django.http import FileResponse, HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from .Revision_utils import *
from .db_locking import locker
from .forms import NewsCommentForm, RevisionItemEntryFullForm
from .models import NewsEntry
from .perms_utils import *

root = Path(__file__).resolve().parent.parent.parent
with open(root / "VERSION") as fp:
    lines = fp.readlines()
SiteVersion = lines[0].strip()
SiteHash = lines[1].strip()
staff_active = settings.ENABLE_STAFF


def news(request):
    """
    Main Page, with news.
    :param request: the page request
    :return: the rendered page
    """
    news_list = NewsEntry.objects.order_by("-date")[:15]
    return render(
        request,
        "delivery/news.html",
        {
            "title": "news",
            "page": "news",
            "has_menu": True,
            "has_submenu": False,
            "news_list": news_list,
            "staff_active": staff_active,
            "is_admin": can_see_admin(request),
            "version": {"number": SiteVersion, "hash": SiteHash},
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
    return render(
        request,
        "delivery/news_detail.html",
        {
            "title": "news",
            "page": "news",
            "has_menu": True,
            "has_submenu": False,
            "news_item": news_item,
            "comment_form": comment_form,
            "new_comment": new_comment,
            "staff_active": staff_active,
            "is_admin": can_see_admin(request),
            "version": {"number": SiteVersion, "hash": SiteHash},
        },
    )


def branches(request):
    """

    :param request:
    :return:
    """
    branch_list = get_visible_branches_info()

    return render(
        request,
        "delivery/branches.html",
        {
            "title": "Branches",
            "page": "revisions",
            "has_menu": True,
            "has_submenu": False,
            "staff_active": staff_active,
            "is_admin": can_see_admin(request),
            "branch_list": branch_list,
            "version": {"number": SiteVersion, "hash": SiteHash},
        },
    )


def revisions(request, rev_branch: str):
    """

    :param rev_branch:
    :param request:
    :return:
    """
    current_revision = None
    older_revisions = []
    branch_filter = rev_branch
    # get last hash
    if get_revision_count(branch_filter) > 0:
        hashes = get_revision_hashes(branch_filter)
        current_revision = {
            "hash": hashes[0],
            "date": get_revision_date(hashes[0]),
        }
        for rev_hash in hashes[1:]:
            older_revisions.append(
                {"hash": rev_hash, "date": get_revision_date(rev_hash)}
            )

    return render(
        request,
        "delivery/revisions.html",
        {
            "title": f"revisions - branch: {rev_branch}",
            "page": "revisions",
            "has_menu": True,
            "has_submenu": False,
            "staff_active": staff_active,
            "is_admin": can_see_admin(request),
            "branch": get_branch_info(rev_branch),
            "current_revision": current_revision,
            "older_revisions": older_revisions,
            "version": {"number": SiteVersion, "hash": SiteHash},
        },
    )


def revision_detail(request, rev_hash):
    """

    :param request:
    :param rev_hash:
    :return:
    """
    current_revision = get_revision_info(rev_hash)

    return render(
        request,
        "delivery/revision_detail.html",
        {
            "title": f"revision - hash: {current_revision['hash']} - branch: {current_revision['branch']}",
            "page": "revisions",
            "has_menu": True,
            "has_submenu": False,
            "staff_active": staff_active,
            "is_admin": can_see_admin(request),
            "revision": current_revision,
            "version": {"number": SiteVersion, "hash": SiteHash},
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
    if can_see_revision_admin(request):
        return redirect("a_revisions")
    return redirect("a_users")


def dl_script(request):
    file = Path(f"{settings.STATICFILES_DIRS}/scripts/api.py")
    response = FileResponse(open(file, "rb"))
    response["Content-Disposition"] = 'attachement; filename="api.py"'
    return response


def entry_exists(request):
    data = request.POST.dict()
    file_name = ""
    if len(request.FILES.dict()) > 0:
        file_name = request.FILES.dict().keys()[0]
    elif "package.path" in data:
        file_name = data["package.name"]
    new_path = (
        Path(settings.MEDIA_ROOT)
        / "packages"
        / data["branch"]
        / data["hash"]
        / file_name
    )
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
                    key, dec = (
                        b64decode(request.headers["Authorization"].split()[-1])
                        .decode("ascii")
                        .split(":", 1)
                    )
                    user = authenticate(request, username=key, password=dec)
                    if user is None:
                        return HttpResponseForbidden(
                            f"""Only authenticated user allowed 
    Login: {key}, password: {dec} is invalid."""
                        )
                    login(request, user)
                except Exception as err:
                    return HttpResponseForbidden(
                        f"""Only authenticated user allowed 
    Method: {request.method},Headers: {request.headers}
    ERROR: {err}"""
                    )
            if not request.user.is_authenticated:
                return HttpResponseForbidden(f"""Only authenticated user allowed""")
        if locker.is_locked():
            return HttpResponse(
                f"ERROR: Server is under maintenance, try again later.", status=406
            )
        if request.method == "GET":
            # if get method, simply DL the api script
            return dl_script(request)
        if request.method != "POST":
            return HttpResponse(
                f"ERROR invalid action.\nMETHOD: {request.method}\nheaders: {request.headers}",
                status=406,
            )
        data = request.POST.dict()
        if "action" not in data:
            return HttpResponse(
                f"ERROR no asked action.\nPOST: {data}\nheaders: {request.headers}",
                status=406,
            )
        action = data["action"]
        if action == "version":
            return HttpResponse(f"version: {SiteVersion}\n", status=200)
        elif action == "pull":
            return HttpResponse(
                f"""ERROR PULL function is not yet implemented.""", status=406
            )
        elif action == "push":
            if not request.user.has_perm("delivery.add_revisionitementry"):
                return HttpResponseForbidden("Please ask the right to delete packages")
            try:
                if len(request.FILES.dict()) > 0:
                    form = RevisionItemEntryFullForm(request.POST, request.FILES)
                    if form.is_valid():
                        if entry_exists(request):
                            return HttpResponse(
                                f"WARNING: Entry already exists.",
                                status=201,
                            )
                        form.save()
                        return HttpResponse(
                            f"GOOD.\nPOST: {data}\nFILES: {request.FILES.dict()}\nheaders: {request.headers}",
                            status=200,
                        )
                    else:
                        form.full_clean()
                        return HttpResponse(
                            f"INVALID FORM.\nPOST: {data}\nFILES: {request.FILES.dict()}\nheaders: {request.headers}",
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
                            f"ERROR INVALID REQUEST.\n"
                            f"POST: {data}\n"
                            f"ERROR  Missing data: {missing}\n"
                            f"headers: {request.headers}",
                            status=406,
                        )
                    origin_path = Path((data["package.path"]))
                    new_path = (
                        Path(settings.MEDIA_ROOT)
                        / "packages"
                        / data["branch"]
                        / data["hash"]
                        / data["package.name"]
                    )
                    if entry_exists(request):
                        return HttpResponse(
                            f"WARNING: Entry already exists.",
                            status=201,
                        )
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    move(origin_path, new_path)
                    entry = RevisionItemEntry.objects.create(
                        hash=data["hash"],
                        branch=data["branch"],
                        name=data["name"],
                        flavor_name=data["flavor_name"],
                        rev_type=data["rev_type"],
                        date=data["date"],
                        package=str(new_path),
                    )
                    entry.save()
                    return HttpResponse(
                        f"GOOD.\nPOST: {data}\nheaders: {request.headers}",
                        status=200,
                    )
                else:
                    return HttpResponse(
                        f"ERROR  INVALID REQUEST.\n"
                        f"POST: {data}\n"
                        f"ERROR NO FILE\n"
                        f"headers: {request.headers}",
                        status=406,
                    )
            except Exception as err:
                return HttpResponse(
                    f"ERROR problem with the data: {err}.\n"
                    f"POST: {data}\n"
                    f"FILES: {request.FILES.dict()}\n"
                    f"headers: {request.headers}\n ",
                    status=406,
                )
        elif action == "push_doc":
            if not request.user.has_perm("delivery.add_revisionitementry"):
                return HttpResponseForbidden("Please ask the right to delete packages")
            try:
                if "package.path" in data:
                    if "branch" not in data.keys():
                        return HttpResponse(
                            f"ERROR INVALID REQUEST.\n"
                            f"POST: {data}\n"
                            f"ERROR  Missing branch field\n"
                            f"headers: {request.headers}",
                            status=406,
                        )
                    origin_path = Path(data["package.path"])
                    if not origin_path.exists():
                        return HttpResponse(
                            f"ERROR  INVALID REQUEST.\n"
                            f"POST: {data}\n"
                            f"ERROR NO FILE {origin_path} exists in defined package field.\n"
                            f"headers: {request.headers}",
                            status=406,
                        )
                    origin_path_name = Path(data["package.name"])
                    new_path = (
                        Path(settings.MEDIA_ROOT) / "documentation" / data["branch"]
                    )

                    if new_path.exists():
                        if not new_path.is_dir():
                            new_path.unlink(missing_ok=True)
                        else:
                            shutil.rmtree(new_path, ignore_errors=True)
                    new_path.mkdir(parents=True)
                    suffixes = "".join(origin_path_name.suffixes)
                    if suffixes == ".zip":
                        with zipfile.ZipFile(origin_path, "r") as zip_ref:
                            zip_ref.extractall(new_path)
                    elif suffixes in [".tar.gz", ".tgz"]:
                        with tarfile.open(origin_path, "r:gz") as tar_ref:
                            tar_ref.extractall(new_path)
                    else:
                        return HttpResponse(
                            f"ERROR  INVALID REQUEST.\n"
                            f"POST: {data}\n"
                            f"ERROR FILE {origin_path_name} Format not supported {suffixes}.\n"
                            f"headers: {request.headers}",
                            status=406,
                        )
                    return HttpResponse(
                        f"GOOD.\nPOST: {data}\nheaders: {request.headers}",
                        status=200,
                    )
                else:
                    return HttpResponse(
                        f"ERROR  INVALID REQUEST.\n"
                        f"POST: {data}\n"
                        f"ERROR NO FILE in package field.\n"
                        f"headers: {request.headers}",
                        status=406,
                    )
            except Exception as err:
                return HttpResponse(
                    f"ERROR problem with the data: {err}.\n"
                    f"POST: {data}\n"
                    f"FILES: {request.FILES.dict()}\n"
                    f"headers: {request.headers}\n ",
                    status=406,
                )
        elif action == "delete":
            if not request.user.has_perm("delivery.delete_revisionitementry"):
                return HttpResponseForbidden("Please ask the right to delete packages")
            objs = find_revision(data)
            if len(objs) == 0:
                return HttpResponse(f"""ERROR No matching package.""", status=406)
            if len(objs) > 1:
                return HttpResponse(
                    f"""ERROR more than one package match the query.""", status=406
                )
            objs[0].delete()
        else:
            return HttpResponse(
                f"ERROR invalid action.\nPOST: {data}\nheaders: {request.headers}",
                status=406,
            )
    except Exception as err:
        return HttpResponse(f"""ERROR Exception during treatment {err}.""", status=406)
