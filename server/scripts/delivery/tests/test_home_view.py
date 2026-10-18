"""
Tests of the home page (`/`).
"""

from datetime import timedelta

from django.utils import timezone

from delivery.models import NewsEntry
from delivery.models_pages import PageSection
from delivery.pages_seed import seed_pages

from .helpers import PagesTestCase, make_item


def make_news(count, start=None):
    start = start or timezone.now()
    return [
        NewsEntry.objects.create(title=f"News {index}", slug=f"news-{index}", date=start - timedelta(days=index))
        for index in range(count)
    ]


class HomeViewTest(PagesTestCase):
    def test_renders_with_an_empty_database(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<h1", count=1)
        self.assertContains(response, 'href="/presentation"')
        self.assertNotContains(response, 'id="download"')
        self.assertNotContains(response, 'id="news"')

    def test_discover_links_to_the_presentation(self):
        seed_pages()
        response = self.client.get("/")
        self.assertContains(response, "Discover Owl Engine")
        self.assertContains(response, 'class="btn btn--primary btn--lg" href="/presentation"')

    def test_download_button_leads_to_the_release_section(self):
        seed_pages()
        make_item("0.3.0", "aaa111", stable=True)
        response = self.client.get("/")
        self.assertContains(response, 'href="/presentation#release"')
        self.assertContains(response, "Download v0.3.0")
        self.assertContains(response, 'href="/branches"')

    def test_download_button_falls_back_to_the_branches(self):
        seed_pages()
        make_item("0.3.0", "aaa111", stable=True)
        PageSection.objects.filter(page="presentation", key="release").update(enabled=False)
        response = self.client.get("/")
        self.assertNotContains(response, "/presentation#release")
        self.assertContains(response, "Download v0.3.0")

    def test_download_without_release_keeps_all_downloads(self):
        seed_pages()
        make_item("0.4.0", "bbb222")
        response = self.client.get("/")
        self.assertContains(response, 'id="download"')
        self.assertContains(response, "All downloads")
        self.assertNotContains(response, "Latest release")

    def test_three_latest_published_news_and_all_news(self):
        seed_pages()
        news = make_news(5)
        news[1].published = False
        news[1].save()
        response = self.client.get("/")
        for shown in (news[0], news[2], news[3]):
            self.assertContains(response, shown.title)
        self.assertNotContains(response, news[1].title)
        self.assertNotContains(response, news[4].title)
        self.assertContains(response, 'href="/news"')
        self.assertContains(response, "All news")

    def test_drafts_only_in_preview_for_an_editor(self):
        seed_pages()
        draft = NewsEntry.objects.create(title="Draft news", slug="draft", published=False)
        self.assertNotContains(self.client.get("/?preview=1"), draft.title)
        self.client.force_login(self.make_editor())
        self.assertNotContains(self.client.get("/"), draft.title)
        self.assertContains(self.client.get("/?preview=1"), draft.title)

    def test_disabled_section_is_absent(self):
        seed_pages()
        make_news(1)
        PageSection.objects.filter(page="home", key="news").update(enabled=False)
        self.assertNotContains(self.client.get("/"), 'id="news"')

    def test_next_render_shows_a_change(self):
        seed_pages()
        news = make_news(1)[0]
        self.assertContains(self.client.get("/"), "News 0")
        news.title = "Renamed news"
        news.save()
        self.assertContains(self.client.get("/"), "Renamed news")

    def test_news_list_keeps_every_published_news(self):
        news = make_news(5)
        news[0].published = False
        news[0].save()
        response = self.client.get("/news")
        for shown in news[1:]:
            self.assertContains(response, shown.title)
        self.assertNotContains(response, news[0].title)

    def test_draft_news_detail_is_hidden(self):
        draft = NewsEntry.objects.create(title="Draft news", slug="draft", published=False)
        self.assertEqual(self.client.get(f"/news/{draft.pk}").status_code, 404)
