"""
Tests of the news, downloads and documentation pages.
"""

from datetime import timedelta
from pathlib import Path

from django.utils import timezone

from delivery.models import BranchEntry, NewsEntry
from delivery.models_pages import ReleaseNote

from .helpers import MediaTestCase, make_item


def make_news(count):
    now = timezone.now()
    return [
        NewsEntry.objects.create(title=f"News {index}", slug=f"n{index}", date=now - timedelta(days=index))
        for index in range(count)
    ]


class NewsPagesTest(MediaTestCase):
    def test_news_list_is_paginated(self):
        make_news(12)
        first = self.client.get("/news")
        self.assertContains(first, '<article class="news-card', count=10)
        self.assertContains(first, "Page 1 of 2")
        self.assertContains(first, 'href="?page=2"')
        second = self.client.get("/news?page=2")
        self.assertContains(second, "News 11")
        self.assertNotContains(second, "news-card--latest")

    def test_news_detail_links_its_neighbours(self):
        news = make_news(3)
        response = self.client.get(f"/news/{news[1].pk}")
        self.assertContains(response, "<title>News 1 — Owl Engine</title>")
        self.assertContains(response, f'href="/news/{news[0].pk}"')
        self.assertContains(response, f'href="/news/{news[2].pk}"')
        self.assertContains(response, "Log in to leave a comment")

    def test_draft_is_not_a_neighbour(self):
        news = make_news(3)
        news[0].published = False
        news[0].save()
        self.assertNotContains(self.client.get(f"/news/{news[1].pk}"), f'href="/news/{news[0].pk}"')


class DownloadPagesTest(MediaTestCase):
    def test_latest_release_is_the_highest_stable_version(self):
        make_item("0.10.0", "aaa111", stable=True)
        make_item("0.9.0", "bbb222", stable=True)
        make_item("0.11.0", "ccc333")
        ReleaseNote.objects.create(branch="0.10.0", title="Owl Engine 0.10.0 — Big")
        response = self.client.get("/branches")
        content = response.content.decode()
        self.assertContains(response, "Owl Engine 0.10.0 — Big")
        self.assertContains(response, "Owl Engine — Linux x64")
        self.assertLess(content.index("Development builds"), content.index("Older releases"))
        self.assertIn('href="/revisions/0.9.0"', content)
        self.assertIn('href="/revisions/0.11.0"', content)

    def test_branch_page_shows_the_newest_downloads(self):
        make_item("0.3.0", "old000", stable=True)
        make_item("0.3.0", "new111", flavor="windows x64")
        response = self.client.get("/revisions/0.3.0")
        self.assertContains(response, "Owl Engine — Windows x64")
        self.assertContains(response, 'href="/revision/old000"')

    def test_unknown_or_hidden_branch_is_404(self):
        make_item("0.3.0", "aaa111")
        BranchEntry.objects.filter(name="0.3.0").update(visible=False)
        self.assertEqual(self.client.get("/revisions/0.3.0").status_code, 404)
        self.assertEqual(self.client.get("/revisions/nope").status_code, 404)

    def test_unknown_revision_is_404(self):
        self.assertEqual(self.client.get("/revision/nope").status_code, 404)

    def test_revision_page(self):
        make_item("0.3.0", "aaa111", name="Owl Nest", flavor="linux arm64")
        response = self.client.get("/revision/aaa111")
        self.assertContains(response, "Owl Nest — Linux arm64")
        self.assertContains(response, "Newest of 0.3.0")


class DocsPageTest(MediaTestCase):
    def setUp(self):
        super().setUp()
        make_item("0.3.0", "aaa111", stable=True)
        make_item("0.2.0", "bbb222", stable=True)
        for branch in ("0.3.0", "0.2.0"):
            folder = Path(self.media_root) / "documentation" / branch
            folder.mkdir(parents=True)
            (folder / "index.html").write_text("<html><title>Doc</title></html>")

    def test_docs_page_frames_the_doxygen_tree(self):
        response = self.client.get("/docs/0.3.0/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'src="/media/documentation/0.3.0/index.html"')
        self.assertContains(response, "site-header")
        self.assertContains(response, 'href="/docs/0.2.0/"')
        self.assertNotContains(response, "site-footer")

    def test_deep_link(self):
        response = self.client.get("/docs/0.3.0/classes.html")
        self.assertContains(response, 'src="/media/documentation/0.3.0/classes.html"')

    def test_docs_links_point_at_the_frame(self):
        self.assertContains(self.client.get("/branches"), 'href="/docs/0.3.0/"')
        self.assertContains(self.client.get("/news"), 'href="/docs/0.3.0/"')

    def test_unknown_branch_or_climbing_path_is_404(self):
        self.assertEqual(self.client.get("/docs/0.9.0/").status_code, 404)
        self.assertEqual(self.client.get("/docs/0.3.0/../../delivery.db").status_code, 404)


class ErrorPagesTest(MediaTestCase):
    def test_404_uses_the_site_layout(self):
        response = self.client.get("/no-such-page")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "No such page exists.", status_code=404)
        self.assertContains(response, 'href="/presentation"', status_code=404)
