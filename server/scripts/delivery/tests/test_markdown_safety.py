"""
Markdown written on the site is rendered without anything that runs in the reader's browser.
"""

from django.contrib.auth.models import Permission, User
from django.test import TestCase

from delivery.markdown_utils import markdownify_safe
from delivery.models import NewsEntry
from delivery.models_pages import FeatureCard

PAYLOAD = 'Hi <script>alert(1)</script><img src=x onerror="alert(2)"> [link](javascript:alert(3)) <b onclick=x>b</b>'


class MarkdownifySafeTest(TestCase):
    def assert_harmless(self, html):
        for needle in ("<script", "onerror", "javascript:", "onclick"):
            self.assertNotIn(needle, html)

    def test_scripts_handlers_and_js_links_are_removed(self):
        html = markdownify_safe(PAYLOAD)
        self.assert_harmless(html)
        self.assertIn("<b>b</b>", html)

    def test_markdown_output_is_kept(self):
        html = markdownify_safe(
            "# Title\n\n**bold** [site](/news/1) ![shot](/media/markdownx/a.png)\n\n"
            "| a | b |\n|---|---|\n| 1 | 2 |\n\n```python\nprint(1)\n```\n"
        )
        for needle in ("<h1>", "<strong>bold</strong>", 'href="/news/1"', 'src="/media/markdownx/a.png"', "<table>"):
            self.assertIn(needle, html)
        self.assertIn('class="codehilite"', html)

    def test_models_render_safely(self):
        news = NewsEntry.objects.create(title="T", slug="t", content=PAYLOAD)
        self.assert_harmless(news.content_all_md())
        self.assert_harmless(news.content_md())
        self.assert_harmless(FeatureCard(title="C", body=PAYLOAD).body_md())

    def test_comment_cannot_attack_the_moderator(self):
        news = NewsEntry.objects.create(title="T", slug="t")
        author = User.objects.create_user("visitor", password="visitor-password")
        self.client.force_login(author)
        self.client.post(f"/news/{news.pk}", {"content": PAYLOAD})
        moderator = User.objects.create_user("moderator", password="moderator-password")
        moderator.user_permissions.add(Permission.objects.get(codename="delete_newscomment"))
        self.client.force_login(moderator)
        response = self.client.get(f"/admin/news/{news.pk}")
        self.assertEqual(response.status_code, 200)
        # The page has scripts of its own: look for the payload instead.
        self.assertNotIn("alert(", response.content.decode())
        self.assertContains(response, "<b>b</b>")

    def test_editor_preview_is_sanitized(self):
        self.client.force_login(User.objects.create_user("writer", password="writer-password"))
        response = self.client.post("/markdownx/markdownify/", {"content": PAYLOAD})
        self.assertEqual(response.status_code, 200)
        self.assert_harmless(response.content.decode())
