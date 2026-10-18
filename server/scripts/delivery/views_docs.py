"""
The engine documentation, shown inside the site: the header of the site above the doxygen pages.
"""

from django.http import Http404
from django.shortcuts import render

from .models import BranchEntry
from .revision_utils import get_branch_documentation, get_branch_documentation_raw_url, get_documented_branches
from .views_pages import page_context


def docs(request, branch, page=""):
    """
    Frame around the doxygen tree of a branch; `page` opens a page of the tree directly.
    """
    if ".." in page.split("/") or page.startswith("/"):
        raise Http404("No such documentation page.")
    if not BranchEntry.objects.filter(name=branch, visible=True).exists() or not get_branch_documentation(branch):
        raise Http404("No documentation for this branch.")
    context = page_context(request, "docs")
    context.update(
        {
            "branch": branch,
            "frame_url": get_branch_documentation_raw_url(branch, page or "index.html"),
            "raw_root": get_branch_documentation_raw_url(branch),
            "other_branches": [name for name in get_documented_branches() if name != branch],
            "hide_footer": True,
        }
    )
    return render(request, "delivery/docs.html", context)
