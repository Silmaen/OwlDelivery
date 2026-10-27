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
from django.contrib.auth.models import Group, User
from django.db.models import Count, Max, Q
from django.db.models.functions import TruncDate, TruncWeek
from django.utils import timezone

from .models_stats import HIT_DOWNLOAD, HIT_PAGE, TrafficHit

# Members of this group are scripts (CI, monitoring): their hits leave the statistics unless asked for.
SERVICE_GROUP = "Service accounts"
# Codename of the permission of the Statistics tab: its holders count as admins.
STATS_PERMISSION = "view_traffichit"
# Hits older than this are deleted at container start (management command purge_stats).
STATS_RETENTION_DAYS = 400
# Periods offered by the admin page, in days; above WEEKLY_ABOVE_DAYS the chart counts per week.
STATS_PERIODS = (7, 30, 90, 365)
STATS_DEFAULT_PERIOD = 30
WEEKLY_ABOVE_DAYS = 90
STATS_TOP_ROWS = 20
# A visit (or a signed-in user) with at least this many page views counts as engaged, not a bounce.
ENGAGED_PAGES = 2
# Places, networks and referrers shown per signed-in user.
USER_TOP_VALUES = 3
# User agents of robots, crawlers, link previews and command-line clients (the engine CI uses requests).
AUTOMATED_AGENTS = re.compile(
    r"bot|crawl|spider|slurp|archiver|facebookexternalhit|embedly|preview|lighthouse|headless|monitor|uptime|"
    r"gatus|curl|wget|python|requests|httpx|aiohttp|go-http|okhttp|java/|libwww|scrapy|feedfetcher",
    re.IGNORECASE,
)
# Name of a robot inside its user agent ("Googlebot/2.1", "compatible; bingbot"), else the first product token.
BOT_NAME = re.compile(r"[A-Za-z][\w.-]*(?:bot|crawler|spider|slurp|archiver|fetcher)\b", re.IGNORECASE)
COMPATIBLE_NAME = re.compile(r"compatible;\s*([^;/)]+)")
PRODUCT_NAME = re.compile(r"^([A-Za-z][\w.-]*)")
# Files of `settings.GEOIP_DIR` (management command update_geoip). country.mmdb is the database of 0.5.1's first
# version: still read for the country until city.mmdb replaces it.
GEOIP_FILES = {"city": "city.mmdb", "asn": "asn.mmdb", "country": "country.mmdb"}
_geoip = {}


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


def agent_name(agent):
    """
    Short name of a robot or script, from its user agent.
    """
    if not agent:
        return "(no user agent)"
    for pattern in (BOT_NAME, COMPATIBLE_NAME):
        match = pattern.search(agent)
        if match:
            return match.group(match.lastindex or 0).strip()[:64]
    product = PRODUCT_NAME.match(agent)
    if product and product.group(1).lower() != "mozilla":
        return product.group(1)[:64]
    keyword = AUTOMATED_AGENTS.search(agent)
    return keyword.group(0).lower() if keyword else "(other)"


def visitor_hash(address, agent):
    """
    The same visitor gives the same hash for one day; the address cannot be read back from it.
    """
    message = f"{timezone.localdate().isoformat()}|{address or ''}|{agent}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()[:16]


def get_geoip_reader(name):
    """
    Reader of one database of `GEOIP_FILES`, reopened when its file changes; None without it.
    """
    path = Path(settings.GEOIP_DIR) / GEOIP_FILES[name]
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    cached = _geoip.get(name)
    if cached is None or cached[0] != mtime:
        try:
            reader = maxminddb.open_database(str(path))
        except (OSError, ValueError, maxminddb.InvalidDatabaseError):
            reader = None
        cached = _geoip[name] = (mtime, reader)
    return cached[1]


def read_record(name, address):
    reader = get_geoip_reader(name)
    if reader is None:
        return {}
    try:
        return reader.get(str(address)) or {}
    except (ValueError, maxminddb.InvalidDatabaseError):
        return {}


def english_name(entry):
    return str(((entry or {}).get("names") or {}).get("en", ""))[:100]


def lookup_location(address):
    """
    Country code, region, city and network (ISP or organisation) of a public address; "" for what is unknown.
    """
    location = {"country": "", "region": "", "city": "", "network": ""}
    if address is None or address.is_private or address.is_loopback:
        return location
    record = read_record("city", address) or read_record("country", address)
    location["country"] = str((record.get("country") or {}).get("iso_code", ""))[:2].upper()
    location["region"] = english_name((record.get("subdivisions") or [{}])[0])
    location["city"] = english_name(record.get("city"))
    location["network"] = str(read_record("asn", address).get("autonomous_system_organization", ""))[:100]
    return location


def has_location_data():
    return any(get_geoip_reader(name) is not None for name in GEOIP_FILES)


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
    automated = is_automated(agent)
    user = getattr(request, "user", None)
    return TrafficHit.objects.create(
        kind=kind,
        path=path[:255],
        item=item,
        user=user if user is not None and user.is_authenticated else None,
        automated=automated,
        agent=agent_name(agent) if automated else "",
        visitor=visitor_hash(address, agent),
        referrer=referrer_host(request),
        **lookup_location(address),
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


def admin_user_ids():
    """
    The admins: superusers, staff, and whoever may read the statistics (permission given directly or by a group).
    """
    return set(
        User.objects.filter(
            Q(is_superuser=True)
            | Q(is_staff=True)
            | Q(user_permissions__codename=STATS_PERMISSION, user_permissions__content_type__app_label="delivery")
            | Q(groups__permissions__codename=STATS_PERMISSION, groups__permissions__content_type__app_label="delivery")
        ).values_list("pk", flat=True)
    )


def filter_audience(hits, admins=False, services=False, automated=False):
    """
    Remove the hits of the admins (`admin_user_ids`), of the service accounts and of the robots.
    """
    if not admins:
        hits = hits.exclude(user_id__in=admin_user_ids())
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


def place_label(country, region, city):
    """
    "City, Region, FR" with what is known; "" when nothing is.
    """
    return ", ".join(part for part in (city, region if region != city else "", country) if part)


def top_values(pairs, limit=USER_TOP_VALUES):
    """
    {key: [(value, count), ...]} from (key, value, count) rows, the `limit` most frequent values per key.
    """
    grouped = {}
    for key, value, count in pairs:
        grouped.setdefault(key, {})
        grouped[key][value] = grouped[key].get(value, 0) + count
    return {
        key: sorted(values.items(), key=lambda pair: (-pair[1], pair[0]))[:limit] for key, values in grouped.items()
    }


def get_user_rows(hits, since):
    """
    Signed-in users, with their role (admin, service account or user), where they connect from and the sites
    they came from. A visitor lands before signing in: the referrer is read on every hit of the same daily
    visitor hash, the anonymous ones before the login included.
    """
    admin_ids = admin_user_ids()
    service_ids = set(Group.objects.filter(name=SERVICE_GROUP).values_list("user__id", flat=True))
    signed_in = hits.exclude(user=None)
    rows = (
        signed_in.values("user_id", "user__username")
        .annotate(
            views=Count("id", filter=Q(kind=HIT_PAGE)),
            downloads=Count("id", filter=Q(kind=HIT_DOWNLOAD)),
            visits=Count("visitor", distinct=True),
            last=Max("date"),
        )
        .order_by("-views", "-downloads", "user__username")
    )
    places = top_values(
        (row["user_id"], place_label(row["country"], row["region"], row["city"]) or "Unknown", row["n"])
        for row in signed_in.values("user_id", "country", "region", "city").annotate(n=Count("id"))
    )
    networks = top_values(
        (row["user_id"], row["network"], row["n"])
        for row in signed_in.exclude(network="").values("user_id", "network").annotate(n=Count("id"))
    )
    visitor_users = {}
    for user_id, visitor in signed_in.values_list("user_id", "visitor").distinct():
        visitor_users.setdefault(visitor, set()).add(user_id)
    referrers = top_values(
        (user_id, row["referrer"], row["n"])
        for row in TrafficHit.objects.filter(date__gte=since, visitor__in=list(visitor_users))
        .exclude(referrer="")
        .values("visitor", "referrer")
        .annotate(n=Count("id"))
        for user_id in visitor_users[row["visitor"]]
    )
    result = []
    for row in rows:
        user_id = row["user_id"]
        if user_id in admin_ids:
            role = "admin"
        elif user_id in service_ids:
            role = "service"
        else:
            role = "user"
        result.append(
            {
                **row,
                "role": role,
                "places": places.get(user_id, []),
                "networks": networks.get(user_id, []),
                "referrers": referrers.get(user_id, []),
            }
        )
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


def get_city_rows(hits):
    rows = (
        hits.exclude(city="", region="")
        .values("country", "region", "city")
        .annotate(
            views=Count("id", filter=Q(kind=HIT_PAGE)),
            visits=Count("visitor", filter=Q(kind=HIT_PAGE), distinct=True),
            downloads=Count("id", filter=Q(kind=HIT_DOWNLOAD)),
        )
        .order_by("-visits", "-downloads", "country", "city")
    )
    return [
        {**row, "flag": country_flag(row["country"]), "label": place_label("", row["region"], row["city"])}
        for row in rows[:STATS_TOP_ROWS]
    ]


def get_network_rows(hits):
    return list(
        hits.exclude(network="")
        .values("network")
        .annotate(
            views=Count("id", filter=Q(kind=HIT_PAGE)),
            visits=Count("visitor", filter=Q(kind=HIT_PAGE), distinct=True),
            downloads=Count("id", filter=Q(kind=HIT_DOWNLOAD)),
        )
        .order_by("-visits", "-downloads", "network")[:STATS_TOP_ROWS]
    )


def get_robot_rows(robots):
    """
    Robots and scripts by name; the hits recorded before the names were kept have none.
    """
    return list(
        robots.values("agent")
        .annotate(
            views=Count("id", filter=Q(kind=HIT_PAGE)),
            downloads=Count("id", filter=Q(kind=HIT_DOWNLOAD)),
            pages=Count("path", filter=Q(kind=HIT_PAGE), distinct=True),
            networks=Count("network", distinct=True),
            last=Max("date"),
        )
        .order_by("-views", "-downloads", "agent")[:STATS_TOP_ROWS]
    )


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


def count_engaged(pages, field):
    """
    Number of distinct `field` values (visitor hash, user) with at least `ENGAGED_PAGES` page views.
    """
    return pages.values(field).annotate(n=Count("id")).filter(n__gte=ENGAGED_PAGES).count()


def get_report(days=STATS_DEFAULT_PERIOD, admins=False, services=False, automated=False):
    """
    Everything the statistics page shows, over the last `days` days.
    The robots table always lists the robots, whatever `automated` says: it is their detail.
    """
    since = timezone.now() - timedelta(days=days)
    period = TrafficHit.objects.filter(date__gte=since)
    hits = filter_audience(period, admins, services, automated)
    robots = filter_audience(period, admins, services, automated=True).filter(automated=True)
    pages = hits.filter(kind=HIT_PAGE)
    downloads = hits.filter(kind=HIT_DOWNLOAD)
    anonymous = hits.filter(user=None)
    anonymous_pages = anonymous.filter(kind=HIT_PAGE)
    views = pages.count()
    visits = pages.values("visitor").distinct().count()
    return {
        "totals": {
            "views": views,
            "visits": visits,
            "engaged_visits": count_engaged(pages, "visitor"),
            "pages_per_visit": round(views / visits, 1) if visits else 0,
            "downloads": downloads.count(),
            "users": hits.exclude(user=None).values("user").distinct().count(),
            "engaged_users": count_engaged(pages.exclude(user=None), "user"),
            "anonymous_views": anonymous_pages.count(),
            "anonymous_visits": anonymous_pages.values("visitor").distinct().count(),
            "anonymous_downloads": anonymous.filter(kind=HIT_DOWNLOAD).count(),
            "robot_hits": robots.count(),
        },
        "timeline": get_timeline(hits, since, days),
        "top_pages": list(
            pages.values("path")
            .annotate(views=Count("id"), visits=Count("visitor", distinct=True))
            .order_by("-views", "path")[:STATS_TOP_ROWS]
        ),
        "users": get_user_rows(hits, since),
        "countries": get_country_rows(anonymous),
        "cities": get_city_rows(anonymous),
        "networks": get_network_rows(anonymous),
        "referrers": list(
            anonymous_pages.exclude(referrer="")
            .values("referrer")
            .annotate(views=Count("id"), visits=Count("visitor", distinct=True))
            .order_by("-visits", "referrer")[:STATS_TOP_ROWS]
        ),
        "robots": get_robot_rows(robots),
        "packages": get_package_rows(downloads),
        "branches": list(
            downloads.values("item__branch").annotate(downloads=Count("id")).order_by("-downloads", "item__branch")
        ),
        "geoip": has_location_data(),
    }
