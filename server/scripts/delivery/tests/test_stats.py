"""
Traffic statistics: page views, downloads mirrored by nginx, the Statistics admin tab.
"""

from datetime import timedelta
from io import StringIO
from unittest import mock

from django.contrib.auth.models import Group, Permission, User
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.utils import timezone

from delivery.models import TrafficHit
from delivery.models_stats import HIT_DOWNLOAD, HIT_PAGE
from delivery.stats_utils import (
    SERVICE_GROUP,
    agent_name,
    client_address,
    country_flag,
    get_report,
    place_label,
    purge_old_hits,
)

from .helpers import MediaTestCase, make_item

BROWSER = "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0"
# Behind swag: the visitor, then the TLS proxy appended by nginx; gunicorn only sees nginx.
VISITOR = {"REMOTE_ADDR": "127.0.0.1", "HTTP_X_FORWARDED_FOR": "8.8.8.8, 172.18.0.2", "HTTP_USER_AGENT": BROWSER}


def grant(user, *codenames):
    user.user_permissions.add(*Permission.objects.filter(codename__in=codenames))
    return User.objects.get(pk=user.pk)


class PageViewTest(TestCase):
    def test_a_public_page_is_counted(self):
        self.client.get("/news", **VISITOR)
        hit = TrafficHit.objects.get()
        self.assertEqual((hit.kind, hit.path, hit.user, hit.automated), (HIT_PAGE, "/news", None, False))
        self.assertEqual(len(hit.visitor), 16)
        self.assertNotIn("8.8.8.8", hit.visitor)

    def test_same_visitor_same_day_same_hash(self):
        self.client.get("/news", **VISITOR)
        self.client.get("/branches", **VISITOR)
        self.assertEqual(TrafficHit.objects.values("visitor").distinct().count(), 1)

    def test_signed_in_user_is_recorded(self):
        user = User.objects.create_user("reader", password="reader-password")
        self.client.force_login(user)
        self.client.get("/news", **VISITOR)
        self.assertEqual(TrafficHit.objects.get().user, user)

    def test_health_check_is_not_counted(self):
        self.client.get("/news", REMOTE_ADDR="127.0.0.1", HTTP_USER_AGENT="Wget")
        self.client.get("/news", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="127.0.0.1")
        self.assertFalse(TrafficHit.objects.exists())

    def test_untracked_requests(self):
        self.client.get("/admin", **VISITOR)
        self.client.get("/robots.txt", **VISITOR)
        self.client.get("/news/999", **VISITOR)
        self.client.get("/news?preview=1", **VISITOR)
        self.client.post("/news", **VISITOR)
        self.assertFalse(TrafficHit.objects.exists())

    def test_robots_are_flagged(self):
        self.client.get("/news", **{**VISITOR, "HTTP_USER_AGENT": "Googlebot/2.1"})
        self.client.get("/news", **{**VISITOR, "HTTP_USER_AGENT": "python-requests/2.32"})
        self.assertEqual(TrafficHit.objects.filter(automated=True).count(), 2)

    def test_referrer_keeps_other_sites_only(self):
        self.client.get("/news", **VISITOR, HTTP_REFERER="https://www.github.com/Silmaen/Owl")
        self.client.get("/news", **VISITOR, HTTP_HOST="owl.example.org", HTTP_REFERER="https://owl.example.org/")
        self.assertEqual(sorted(TrafficHit.objects.values_list("referrer", flat=True)), ["", "github.com"])

    def test_location_comes_from_the_public_address(self):
        city = mock.Mock()
        city.get.return_value = {
            "country": {"iso_code": "fr"},
            "subdivisions": [{"names": {"en": "Occitanie"}}],
            "city": {"names": {"en": "Toulouse"}},
        }
        asn = mock.Mock()
        asn.get.return_value = {"autonomous_system_organization": "Orange S.A."}
        with mock.patch(
            "delivery.stats_utils.get_geoip_reader", side_effect=lambda name: {"city": city, "asn": asn}.get(name)
        ):
            self.client.get("/news", **VISITOR)
        city.get.assert_called_once_with("8.8.8.8")
        hit = TrafficHit.objects.get()
        self.assertEqual(
            (hit.country, hit.region, hit.city, hit.network), ("FR", "Occitanie", "Toulouse", "Orange S.A.")
        )

    def test_legacy_country_database_still_read(self):
        country = mock.Mock()
        country.get.return_value = {"country": {"iso_code": "DE"}}
        with mock.patch(
            "delivery.stats_utils.get_geoip_reader", side_effect=lambda name: country if name == "country" else None
        ):
            self.client.get("/news", **VISITOR)
        hit = TrafficHit.objects.get()
        self.assertEqual((hit.country, hit.city, hit.network), ("DE", "", ""))

    def test_robot_names(self):
        self.assertEqual(
            agent_name("Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"), "Googlebot"
        )
        self.assertEqual(agent_name("Mozilla/5.0 (compatible; bingbot/2.0)"), "bingbot")
        self.assertEqual(agent_name("python-requests/2.32.3"), "python-requests")
        self.assertEqual(agent_name("curl/8.5.0"), "curl")
        self.assertEqual(agent_name("Mozilla/5.0 (compatible; Uptime-Kuma/1.23)"), "Uptime-Kuma")
        self.assertEqual(agent_name("Mozilla/5.0 (X11) HeadlessChrome/124.0"), "headless")
        self.assertEqual(agent_name(""), "(no user agent)")
        self.client.get("/news", **{**VISITOR, "HTTP_USER_AGENT": "Googlebot/2.1"})
        self.client.get("/news", **VISITOR)
        self.assertEqual(sorted(TrafficHit.objects.values_list("agent", flat=True)), ["", "Googlebot"])

    def test_place_label(self):
        self.assertEqual(place_label("FR", "Occitanie", "Toulouse"), "Toulouse, Occitanie, FR")
        self.assertEqual(place_label("SG", "Singapore", "Singapore"), "Singapore, SG")
        self.assertEqual(place_label("", "", ""), "")

    def test_client_address_ignores_prepended_hops(self):
        request = RequestFactory().get(
            "/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4, 9.9.9.9, 172.18.0.2"
        )
        self.assertEqual(str(client_address(request)), "9.9.9.9")
        lan = RequestFactory().get("/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="192.168.1.20")
        self.assertEqual(str(client_address(lan)), "192.168.1.20")

    def test_country_flag(self):
        self.assertEqual(country_flag("FR"), "\U0001f1eb\U0001f1f7")
        self.assertEqual(country_flag(""), "")


class DownloadTest(MediaTestCase):
    def setUp(self):
        super().setUp()
        self.item = make_item("main", "abc123")
        self.uri = f"/media/{self.item.package.name}"

    def mirror(self, uri=None, method="get", **extra):
        call = getattr(self.client, method)
        return call("/_stats/download", **VISITOR, HTTP_X_ORIGINAL_URI=uri or self.uri, **extra)

    def test_download_is_counted(self):
        self.assertEqual(self.mirror().status_code, 204)
        hit = TrafficHit.objects.get()
        self.assertEqual((hit.kind, hit.item, hit.path), (HIT_DOWNLOAD, self.item, self.uri))

    def test_quoted_uri(self):
        item = make_item("main", "def456", name="Owl Sample", flavor="linux x64")
        item.package.name = item.package.name.replace("Owl_Sample", "Owl Sample")
        item.save()
        self.mirror(f"/media/{item.package.name}".replace(" ", "%20"))
        self.assertEqual(TrafficHit.objects.get().item, item)

    def test_resumed_head_and_unknown_are_not_counted(self):
        self.mirror(HTTP_RANGE="bytes=1024-")
        self.mirror(method="head")
        self.mirror("/media/packages/main/abc123/missing.zip")
        self.mirror("/media/documentation/main/index.html")
        self.assertFalse(TrafficHit.objects.exists())
        self.mirror(HTTP_RANGE="bytes=0-")
        self.assertEqual(TrafficHit.objects.count(), 1)

    def test_packages_are_split_by_version(self):
        other = make_item("0.5.1", "def456")
        self.mirror()
        self.mirror()
        self.mirror(f"/media/{other.package.name}")
        rows = [(row["item__branch"], row["item__hash"], row["downloads"]) for row in get_report()["packages"]]
        self.assertEqual(rows, [("main", "abc123", 2), ("0.5.1", "def456", 1)])

    def test_deleted_package_keeps_its_hits(self):
        self.mirror()
        self.item.delete()
        hit = TrafficHit.objects.get()
        self.assertIsNone(hit.item)
        self.assertEqual(get_report()["packages"][0]["downloads"], 1)


class StatsReportTest(TestCase):
    def setUp(self):
        self.root = User.objects.create_superuser("root", "root@example.com", "root-password")
        self.ci = User.objects.create_user("ci", password="ci-password")
        Group.objects.get_or_create(name=SERVICE_GROUP)[0].user_set.add(self.ci)
        self.reader = User.objects.create_user("reader", password="reader-password")
        for user in (None, None, self.root, self.ci, self.reader):
            TrafficHit.objects.create(kind=HIT_PAGE, path="/news", user=user, visitor=f"v{user and user.pk}")
        TrafficHit.objects.create(kind=HIT_PAGE, path="/news", visitor="bot", automated=True)
        TrafficHit.objects.create(kind=HIT_PAGE, path="/", visitor="old", date=timezone.now() - timedelta(days=60))

    def test_default_leaves_out_admins_services_and_robots(self):
        report = get_report(30)
        self.assertEqual(report["totals"]["views"], 3)
        self.assertEqual(report["totals"]["visits"], 2)
        self.assertEqual([row["user__username"] for row in report["users"]], ["reader"])
        self.assertEqual(report["totals"]["anonymous_views"], 2)

    def test_audience_can_be_included(self):
        report = get_report(30, admins=True, services=True, automated=True)
        self.assertEqual(report["totals"]["views"], 6)
        roles = {row["user__username"]: row["role"] for row in report["users"]}
        self.assertEqual(roles, {"root": "admin", "ci": "service", "reader": "user"})

    def test_period(self):
        self.assertEqual(get_report(90)["totals"]["views"], 4)
        timeline = get_report(365)["timeline"]
        self.assertTrue(timeline["weekly"])
        self.assertEqual(sum(bar["views"] for bar in timeline["bars"]), 4)
        self.assertEqual(len(get_report(7)["timeline"]["bars"]), 8)

    def test_engaged_visitors_and_users(self):
        TrafficHit.objects.create(kind=HIT_PAGE, path="/", user=self.reader, visitor=f"v{self.reader.pk}")
        totals = get_report(30)["totals"]
        # vNone viewed 2 pages, the reader 2 pages too: both engaged.
        self.assertEqual((totals["engaged_visits"], totals["engaged_users"], totals["pages_per_visit"]), (2, 1, 2.0))
        self.assertEqual(totals["robot_hits"], 1)

    def test_robots_are_always_detailed(self):
        TrafficHit.objects.create(kind=HIT_PAGE, path="/", visitor="bot", automated=True, agent="Googlebot")
        rows = {row["agent"]: row for row in get_report(30)["robots"]}
        self.assertEqual((rows["Googlebot"]["views"], rows[""]["views"]), (1, 1))
        self.assertEqual(rows["Googlebot"]["pages"], 1)

    def test_user_origin_includes_the_visit_before_login(self):
        visitor = f"v{self.reader.pk}"
        TrafficHit.objects.create(kind=HIT_PAGE, path="/", visitor=visitor, referrer="github.com")
        TrafficHit.objects.create(
            kind=HIT_PAGE,
            path="/",
            user=self.reader,
            visitor=visitor,
            country="FR",
            region="Occitanie",
            city="Toulouse",
            network="Orange S.A.",
        )
        row = get_report(30)["users"][0]
        self.assertEqual(row["referrers"], [("github.com", 1)])
        self.assertEqual(row["places"][0], ("Toulouse, Occitanie, FR", 1))
        self.assertEqual(row["networks"], [("Orange S.A.", 1)])

    def test_anonymous_cities_and_networks(self):
        TrafficHit.objects.create(
            kind=HIT_PAGE, path="/", visitor="x", country="FR", region="Brittany", city="Rennes", network="Free SAS"
        )
        report = get_report(30)
        self.assertEqual([row["label"] for row in report["cities"]], ["Rennes, Brittany"])
        self.assertEqual([row["network"] for row in report["networks"]], ["Free SAS"])

    def test_stats_viewers_are_admins(self):
        grant(self.reader, "view_traffichit")
        self.assertEqual(get_report(30)["users"], [])
        viewers = Group.objects.create(name="Viewers")
        viewers.permissions.add(Permission.objects.get(codename="view_traffichit"))
        other = User.objects.create_user("other", password="other-password")
        other.groups.add(viewers)
        TrafficHit.objects.create(kind=HIT_PAGE, path="/news", user=other, visitor="other")
        self.assertEqual(get_report(30)["totals"]["views"], 2)
        roles = {row["user__username"]: row["role"] for row in get_report(30, admins=True)["users"]}
        self.assertEqual((roles["reader"], roles["other"]), ("admin", "admin"))

    def test_purge(self):
        self.assertEqual(purge_old_hits(30), 1)
        self.assertEqual(TrafficHit.objects.count(), 6)


class StatsAdminTest(TestCase):
    def test_access_needs_the_permission(self):
        self.assertRedirects(self.client.get("/admin/stats"), "/", fetch_redirect_response=False)
        user = User.objects.create_user("visitor", password="visitor-password")
        self.client.force_login(user)
        self.assertRedirects(self.client.get("/admin/stats"), "/", fetch_redirect_response=False)
        self.client.force_login(grant(user, "view_traffichit"))
        self.assertRedirects(self.client.get("/admin"), "/admin/stats", fetch_redirect_response=False)
        response = self.client.get("/admin/stats?days=365&admins=1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page views")
        self.assertEqual(response.context["days"], 365)
        self.assertTrue(response.context["audience"]["admins"])

    def test_unknown_period_falls_back(self):
        self.client.force_login(User.objects.create_superuser("root", "root@example.com", "root-password"))
        self.assertEqual(self.client.get("/admin/stats?days=12").context["days"], 30)

    def test_admin_page_views_are_not_counted(self):
        self.client.force_login(User.objects.create_superuser("root", "root@example.com", "root-password"))
        self.client.get("/admin/stats", **VISITOR)
        self.assertFalse(TrafficHit.objects.exists())


class ServiceAccountToggleTest(TestCase):
    def setUp(self):
        self.manager = grant(User.objects.create_user("manager", password="manager-password"), "delete_user")
        self.ci = User.objects.create_user("ci", password="ci-password")
        self.client.force_login(self.manager)

    def test_toggle_service(self):
        self.client.post(f"/admin/user/{self.ci.pk}", {"action": "toggle_service"})
        self.assertTrue(self.ci.groups.filter(name=SERVICE_GROUP).exists())
        self.assertContains(self.client.get("/admin/users"), "smart_toy")
        self.client.post(f"/admin/user/{self.ci.pk}", {"action": "toggle_service"})
        self.assertFalse(self.ci.groups.filter(name=SERVICE_GROUP).exists())

    def test_stats_view_needs_to_be_held(self):
        self.client.post(f"/admin/user/{self.ci.pk}", {"action": "toggle_stats_view"})
        self.assertFalse(User.objects.get(pk=self.ci.pk).has_perm("delivery.view_traffichit"))
        grant(self.manager, "view_traffichit")
        self.client.post(f"/admin/user/{self.ci.pk}", {"action": "toggle_stats_view"})
        self.assertTrue(User.objects.get(pk=self.ci.pk).has_perm("delivery.view_traffichit"))

    def test_staff_is_set_by_a_superuser_only(self):
        self.client.post(f"/admin/user/{self.ci.pk}", {"action": "toggle_staff"})
        self.assertFalse(User.objects.get(pk=self.ci.pk).is_staff)
        self.client.force_login(User.objects.create_superuser("root", "root@example.com", "root-password"))
        self.client.post(f"/admin/user/{self.ci.pk}", {"action": "toggle_staff"})
        self.assertTrue(User.objects.get(pk=self.ci.pk).is_staff)
        self.client.post(f"/admin/user/{self.ci.pk}", {"action": "toggle_staff"})
        self.assertFalse(User.objects.get(pk=self.ci.pk).is_staff)


class PurgeUnnamedRobotsTest(TestCase):
    def test_only_unnamed_robot_hits_go(self):
        for automated, agent in ((True, ""), (True, "Googlebot"), (False, "")):
            TrafficHit.objects.create(kind=HIT_PAGE, path="/", automated=automated, agent=agent)
        call_command("purge_stats", "--unnamed-robots", stdout=StringIO())
        self.assertEqual(
            sorted(TrafficHit.objects.values_list("automated", "agent")), [(False, ""), (True, "Googlebot")]
        )
