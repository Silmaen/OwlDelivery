"""
Tests of the paginated revision admin.
"""

from datetime import timedelta

from django.contrib.auth.models import Permission, User
from django.utils import timezone

from delivery.models import RevisionItemEntry
from delivery.views_admin import REVISION_PER_PAGE

from .helpers import MediaTestCase


class AdminRevisionsTest(MediaTestCase):
    def setUp(self):
        super().setUp()
        now = timezone.now()
        # 20 revisions on 0.3.0 (r00 newest), 3 on 0.4.0; two files each.
        for index in range(20):
            self.make("0.3.0", f"r{index:02d}", now - timedelta(hours=index + 10))
        for index in range(3):
            self.make("0.4.0", f"d{index:02d}", now - timedelta(hours=index))
        manager = User.objects.create_user("manager", password="manager-password")
        manager.user_permissions.add(
            *Permission.objects.filter(codename__in=["add_revisionitementry", "delete_revisionitementry"])
        )
        self.client.force_login(manager)

    def make(self, branch, revision_hash, date):
        for flavor in ("linux x64", "windows x64"):
            RevisionItemEntry.objects.create(
                hash=revision_hash,
                branch=branch,
                name="Owl Engine",
                flavor_name=flavor,
                rev_type="e",
                date=date,
                package=f"packages/{branch}/{revision_hash}/{flavor}.zip",
            )

    def hashes(self, response):
        return [row["hash"] for row in response.context["revision_page"].rows]

    def test_first_page_holds_the_newest_revisions(self):
        response = self.client.get("/admin/revisions")
        self.assertEqual(len(self.hashes(response)), REVISION_PER_PAGE)
        self.assertEqual(self.hashes(response)[:4], ["d00", "d01", "d02", "r00"])
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, 'href="/admin/revisions/2"')

    def test_second_page_and_out_of_range(self):
        self.assertEqual(self.hashes(self.client.get("/admin/revisions/2"))[-1], "r19")
        self.assertEqual(self.hashes(self.client.get("/admin/revisions/99"))[-1], "r19")
        self.assertEqual(self.hashes(self.client.get("/admin/revisions/0"))[0], "d00")

    def test_branch_filter(self):
        response = self.client.get("/admin/revisions?branch=0.4.0")
        self.assertEqual(self.hashes(response), ["d00", "d01", "d02"])
        self.assertNotContains(response, "Page 1 of")
        unknown = self.client.get("/admin/revisions?branch=nope")
        self.assertEqual(len(self.hashes(unknown)), REVISION_PER_PAGE)

    def test_pager_keeps_the_filter(self):
        response = self.client.get("/admin/revisions?branch=0.3.0")
        self.assertContains(response, 'href="/admin/revisions/2?branch=0.3.0"')

    def test_delete_goes_back_to_the_same_page(self):
        response = self.client.post("/admin/mrevision/r18", {"action": "delete", "page": "2", "branch": "0.3.0"})
        self.assertRedirects(response, "/admin/revisions/2?branch=0.3.0", fetch_redirect_response=False)
        self.assertFalse(RevisionItemEntry.objects.filter(hash="r18").exists())
        item = RevisionItemEntry.objects.filter(hash="r17").first()
        response = self.client.post(f"/admin/mrevision_item/{item.pk}", {"action": "delete", "page": "x"})
        self.assertRedirects(response, "/admin/revisions", fetch_redirect_response=False)

    def test_queries_do_not_grow_with_the_history(self):
        self.client.get("/admin/revisions")  # Session and caches warmed up.
        before = self.count_queries()
        for index in range(20, 60):
            self.make("0.3.0", f"r{index:02d}", timezone.now() - timedelta(days=index))
        # The saves bumped content_version: warm the cached site blocks up again.
        self.client.get("/admin/revisions")
        self.assertLessEqual(self.count_queries(), before)

    def count_queries(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as queries:
            self.client.get("/admin/revisions")
        return len(queries)
