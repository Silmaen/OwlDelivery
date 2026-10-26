"""
Traffic statistics: recording of the page views and downloads, and the report of the admin page.
"""

import hashlib
import hmac
import ipaddress
import re
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

import maxminddb
from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models import Count, Max, Q
from django.db.models.functions import TruncDate, TruncWeek
from django.utils import timezone

from .models_stats import HIT_DOWNLOAD, HIT_PAGE, TrafficHit

# Members of this group are scripts (CI, monitoring): their hits leave the statistics unless asked for.
SERVICE_GROUP = "Service accounts"
# Hits older than this are deleted at container start (management command purge_stats).
STATS_RETENTION_DAYS = 400
# Periods offered by the admin page, in days; above WEEKLY_ABOVE_DAYS the chart counts per week.
STATS_PERIODS = (7, 30, 90, 365)
STATS_DEFAULT_PERIOD = 30
WEEKLY_ABOVE_DAYS = 90
STATS_TOP_ROWS = 20
# User agents of robots, crawlers, link previews and command-line clients (the engine CI uses requests).
AUTOMATED_AGENTS = re.compile(
    r"bot|crawl|spider|slurp|archiver|facebookexternalhit|embedly|preview|lighthouse|headless|monitor|uptime|"
    r"gatus|curl|wget|python|requests|httpx|aiohttp|go-http|okhttp|java/|libwww|scrapy|feedfetcher",
    re.IGNORECASE,
)
_geoip = {"reader": None, "mtime": None}


def parse_address(text):
    try:
        return ipaddress.ip_address(text.strip())
    except ValueError:
        return None


def client_address(request):
    """
    Address of the visitor: the last public hop of X-Forwarded-For, nginx and the TLS proxy being private ones.
    A client can prepend any address to the header, never append one, so the rightmost public hop is the real one.
    """
    hops = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")
    hops.append(request.META.get("REMOTE_ADDR", ""))
    addresses = [address for address in map(parse_address, hops) if address is not None]
    for address in reversed(addresses):
        if not (address.is_private or address.is_loopback or address.is_link_local):
            return address
    return addresses[0] if addresses else None


def is_automated(agent):
    return not agent or bool(AUTOMATED_AGENTS.search(agent))


def visitor_hash(address, agent):
    """
    The same visitor gives the same hash for one day; the address cannot be read back from it.
    """
    message = f"{timezone.localdate().isoformat()}|{address or ''}|{agent}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()[:16]


def get_geoip_reader():
    """
    Reader of the country database (DB-IP Lite, `update_geoip`), reopened when the file changes; None without it.
    """
    path = Path(settings.GEOIP_PATH)
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    if _geoip["mtime"] != mtime:
        try:
            _geoip["reader"] = maxminddb.open_database(str(path))
        except (OSError, ValueError, maxminddb.InvalidDatabaseError):
            _geoip["reader"] = None
        _geoip["mtime"] = mtime
    return _geoip["reader"]


def lookup_country(address):
    """
    ISO code of the country of a public address, "" when unknown.
    """
    if address is None or address.is_private or address.is_loopback:
        return ""
    reader = get_geoip_reader()
    if reader is None:
        return ""
    try:
        record = reader.get(str(address))
    except (ValueError, maxminddb.InvalidDatabaseError):
        return ""
    country = (record or {}).get("country") or {}
    return str(country.get("iso_code", ""))[:2].upper()


def referrer_host(request):
    """
    Host of the referring site, "" for a link inside the site or no referrer at all.
    """
    host = (urlsplit(request.META.get("HTTP_REFERER", "")).hostname or "").lower()
    if not host:
        return ""
    own_hosts = {settings.DOMAIN_HOST.lower(), request.META.get("HTTP_HOST", "").split(":")[0].lower()}
    if host in own_hosts:
        return ""
    return host.removeprefix("www.")[:255]


def record_hit(request, kind, path, item=None):
    """
    Store one page view or download; requests from the container itself (health check) are not counted.
    :return: The hit, or None when nothing was stored.
    """
    address = client_address(request)
    if address is not None and address.is_loopback:
        return None
    agent = request.META.get("HTTP_USER_AGENT", "")
    user = getattr(request, "user", None)
    return TrafficHit.objects.create(
        kind=kind,
        path=path[:255],
        item=item,
        user=user if user is not None and user.is_authenticated else None,
        automated=is_automated(agent),
        visitor=visitor_hash(address, agent),
        country=lookup_country(address),
        referrer=referrer_host(request),
    )


def purge_old_hits(days=STATS_RETENTION_DAYS):
    deleted, _ = TrafficHit.objects.filter(date__lt=timezone.now() - timedelta(days=days)).delete()
    return deleted


def country_flag(code):
    """
    Flag emoji of an ISO country code.
    """
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(letter) - ord("A")) for letter in code.upper())


def filter_audience(hits, admins=False, services=False, automated=False):
    """
    Remove the hits of the admins (superuser or staff), of the service accounts and of the robots.
    """
    if not admins:
        hits = hits.exclude(Q(user__is_superuser=True) | Q(user__is_staff=True))
    if not services:
        hits = hits.exclude(user__groups__name=SERVICE_GROUP)
    if not automated:
        hits = hits.filter(automated=False)
    return hits


def get_timeline(hits, since, days):
    """
    Page views and downloads per day (per week above `WEEKLY_ABOVE_DAYS`), empty buckets included.
    """
    weekly = days > WEEKLY_ABOVE_DAYS
    trunc = TruncWeek if weekly else TruncDate
    counts = (
        hits.annotate(bucket=trunc("date"))
        .values("bucket")
        .annotate(
            views=Count("id", filter=Q(kind=HIT_PAGE)),
            downloads=Count("id", filter=Q(kind=HIT_DOWNLOAD)),
        )
    )
    by_bucket = {}
    for row in counts:
        bucket = row["bucket"]
        by_bucket[bucket.date() if hasattr(bucket, "date") else bucket] = row
    start = timezone.localtime(since).date()
    step = timedelta(days=7 if weekly else 1)
    if weekly:
        start -= timedelta(days=start.weekday())
    bars = []
    day = start
    today = timezone.localdate()
    while day <= today:
        row = by_bucket.get(day, {})
        bars.append({"day": day, "views": row.get("views", 0), "downloads": row.get("downloads", 0)})
        day += step
    peak = max((bar["views"] + bar["downloads"] for bar in bars), default=0) or 1
    for bar in bars:
        bar["views_pct"] = round(100 * bar["views"] / peak, 1)
        bar["downloads_pct"] = round(100 * bar["downloads"] / peak, 1)
    return {"weekly": weekly, "bars": bars, "peak": peak}


def get_user_rows(hits):
    """
    Signed-in users, with their role: admin, service account or user.
    """
    service_ids = set(Group.objects.filter(name=SERVICE_GROUP).values_list("user__id", flat=True))
    rows = (
        hits.exclude(user=None)
        .values("user_id", "user__username", "user__is_superuser", "user__is_staff")
        .annotate(
            views=Count("id", filter=Q(kind=HIT_PAGE)),
            downloads=Count("id", filter=Q(kind=HIT_DOWNLOAD)),
            last=Max("date"),
        )
        .order_by("-views", "-downloads", "user__username")
    )
    result = []
    for row in rows:
        if row["user__is_superuser"] or row["user__is_staff"]:
            role = "admin"
        elif row["user_id"] in service_ids:
            role = "service"
        else:
            role = "user"
        result.append({**row, "role": role})
    return result


def get_country_rows(hits):
    rows = (
        hits.values("country")
        .annotate(
            views=Count("id", filter=Q(kind=HIT_PAGE)),
            visits=Count("visitor", filter=Q(kind=HIT_PAGE), distinct=True),
            downloads=Count("id", filter=Q(kind=HIT_DOWNLOAD)),
        )
        .order_by("-visits", "-downloads", "country")
    )
    return [{**row, "flag": country_flag(row["country"])} for row in rows[:STATS_TOP_ROWS]]


def get_package_rows(downloads):
    """
    Downloads per package and flavor, all revisions together; a deleted package keeps its hits under no name.
    """
    rows = (
        downloads.values("item__name", "item__flavor_name")
        .annotate(downloads=Count("id"), visits=Count("visitor", distinct=True), last=Max("date"))
        .order_by("-downloads", "item__name", "item__flavor_name")
    )
    return list(rows[:STATS_TOP_ROWS])


def get_report(days=STATS_DEFAULT_PERIOD, admins=False, services=False, automated=False):
    """
    Everything the statistics page shows, over the last `days` days.
    """
    since = timezone.now() - timedelta(days=days)
    hits = filter_audience(TrafficHit.objects.filter(date__gte=since), admins, services, automated)
    pages = hits.filter(kind=HIT_PAGE)
    downloads = hits.filter(kind=HIT_DOWNLOAD)
    anonymous = hits.filter(user=None)
    anonymous_pages = anonymous.filter(kind=HIT_PAGE)
    return {
        "totals": {
            "views": pages.count(),
            "visits": pages.values("visitor").distinct().count(),
            "downloads": downloads.count(),
            "users": hits.exclude(user=None).values("user").distinct().count(),
            "anonymous_views": anonymous_pages.count(),
            "anonymous_visits": anonymous_pages.values("visitor").distinct().count(),
            "anonymous_downloads": anonymous.filter(kind=HIT_DOWNLOAD).count(),
        },
        "timeline": get_timeline(hits, since, days),
        "top_pages": list(
            pages.values("path")
            .annotate(views=Count("id"), visits=Count("visitor", distinct=True))
            .order_by("-views", "path")[:STATS_TOP_ROWS]
        ),
        "users": get_user_rows(hits),
        "countries": get_country_rows(anonymous),
        "referrers": list(
            anonymous_pages.exclude(referrer="")
            .values("referrer")
            .annotate(views=Count("id"), visits=Count("visitor", distinct=True))
            .order_by("-visits", "referrer")[:STATS_TOP_ROWS]
        ),
        "packages": get_package_rows(downloads),
        "branches": list(
            downloads.values("item__branch").annotate(downloads=Count("id")).order_by("-downloads", "item__branch")
        ),
        "geoip": get_geoip_reader() is not None,
    }
