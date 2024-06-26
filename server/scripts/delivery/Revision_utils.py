"""
Utility function for revision manipulation
"""

from .models import RevisionItemEntry


def get_revision_branches():
    revs = RevisionItemEntry.objects.order_by("-date")
    if len(revs) == 0:
        return []
    result = []
    for rev in revs:
        result.append(rev.branch)
    return list(set(result))


def get_revision_hashes(branch_filter=""):
    if branch_filter not in [None, ""]:
        revs = RevisionItemEntry.objects.filter(branch=branch_filter).order_by("-date")
    else:
        revs = RevisionItemEntry.objects.order_by("-date")
    if len(revs) == 0:
        return []
    result = []
    for rev in revs:
        if rev.hash not in result:
            result.append(rev.hash)
    return result


def get_revision_count(branch_filter=""):
    return len(get_revision_hashes(branch_filter))


def get_revision_date(revision_hash):
    revs = RevisionItemEntry.objects.filter(hash=revision_hash).order_by("date")
    if len(revs) == 0:
        return "no date"
    return revs[0].date


def get_revision_name_list(revision_hash):
    revs = RevisionItemEntry.objects.filter(hash=revision_hash).order_by("-date")
    if len(revs) == 0:
        return []
    names = []
    for rev in revs:
        names.append(rev.name)
    names = list(set(names))
    names.sort()
    return names


def get_revision_info(revision_hash):
    revs = RevisionItemEntry.objects.filter(hash=revision_hash).order_by("date")
    if len(revs) == 0:
        return {}
    current_revision = {
        "hash": revs[0].hash,
        "branch": revs[0].branch,
        "date": revs[0].date,
        "item_list": [],
    }
    for name in get_revision_name_list(revision_hash):
        name_revs = revs.filter(name=name)
        item = {
            "name": name,
            "type": name_revs[0].get_pretty_type(),
            "icon": None,
            "flavors": [],
        }
        f = []
        for rev in name_revs:
            f.append(
                {
                    "name": rev.flavor_name,
                    "url": str(rev.package.path).replace("/data/", "/media/"),
                    "size": rev.get_pretty_size_display(),
                    "pk": rev.pk,
                }
            )
        item["flavors"] = f
        current_revision["item_list"].append(item)
    return current_revision


def find_revision(data: dict):
    objs = RevisionItemEntry.objects
    if "hash" in data.keys():
        objs = objs.filter(hash=data["hash"])
    if "branch" in data.keys():
        objs = objs.filter(branch=data["branch"])
    if "name" in data.keys():
        objs = objs.filter(name=data["name"])
    if "flavor_name" in data.keys():
        objs = objs.filter(flavor_name=data["flavor_name"])
    if "date" in data.keys():
        objs = objs.filter(date=data["date"])
    if "rev_type" in data.keys():
        objs = objs.filter(rev_type=data["rev_type"])
    return objs
