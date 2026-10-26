"""
Tests of the Pages tab of the site admin.
"""

from django.contrib.auth.models import Permission, User

from delivery.models_pages import FeatureCard, PageSection, ShowcaseImage, SiteLink, SiteSettings
from delivery.pages_seed import seed_pages
from delivery.views_admin import PAGES_EDIT_CODENAMES, PAGES_PUSH_CODENAMES

from .helpers import PagesTestCase, png_upload


class PagesAdminTest(PagesTestCase):
    def setUp(self):
        super().setUp()
        seed_pages()
        self.editor = User.objects.create_user("editor", password="secret-password")
        self.editor.user_permissions.add(
            *Permission.objects.filter(content_type__app_label="delivery", codename__in=PAGES_EDIT_CODENAMES)
        )

    def login_editor(self):
        self.client.force_login(self.editor)

    def test_anonymous_is_redirected(self):
        response = self.client.get("/admin/pages")
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_tab_visible_only_with_a_page_permission(self):
        other = User.objects.create_user("other", password="secret-password")
        other.user_permissions.add(Permission.objects.get(codename="add_newsentry"))
        self.client.force_login(other)
        self.assertNotContains(self.client.get("/admin/news"), 'href="/admin/pages"')
        self.assertRedirects(self.client.get("/admin/pages"), "/", fetch_redirect_response=False)
        self.login_editor()
        response = self.client.get("/admin/pages")
        self.assertContains(response, 'href="/admin/pages"')
        self.assertContains(response, "Render-style mixing")
        self.assertRedirects(self.client.get("/admin"), "/admin/pages", fetch_redirect_response=False)

    def test_create_edit_delete_a_feature(self):
        self.login_editor()
        response = self.client.post(
            "/admin/pages", {"kind": "feature", "title": "New card", "body": "Body", "order": 9, "published": "on"}
        )
        self.assertRedirects(response, "/admin/pages", fetch_redirect_response=False)
        card = FeatureCard.objects.get(title="New card")
        response = self.client.post(f"/admin/pages/feature/{card.pk}", {"title": "Renamed", "body": "Body", "order": 9})
        self.assertRedirects(response, "/admin/pages", fetch_redirect_response=False)
        card.refresh_from_db()
        self.assertEqual(card.title, "Renamed")
        self.assertFalse(card.published)
        self.client.post(f"/admin/pages/feature/{card.pk}/action", {"action": "delete"})
        self.assertFalse(FeatureCard.objects.filter(pk=card.pk).exists())

    def test_invalid_add_form_shows_its_errors(self):
        self.login_editor()
        response = self.client.post("/admin/pages", {"kind": "link", "label": "No URL", "order": 1})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "form-group__error")

    def test_upload_an_image(self):
        self.login_editor()
        response = self.client.post(
            "/admin/pages",
            {"kind": "image", "key": "hub", "image": png_upload(), "alt_text": "A village", "order": 1},
        )
        self.assertRedirects(response, "/admin/pages", fetch_redirect_response=False)
        self.assertContains(self.client.get("/admin/pages"), "admin-thumb")

    def test_edit_image_texts_without_a_new_file(self):
        self.login_editor()
        self.client.post(
            "/admin/pages",
            {"kind": "image", "key": "hub", "image": png_upload(), "alt_text": "A village", "order": 1},
        )
        image = ShowcaseImage.objects.get(key="hub")
        old_name = image.image.name
        response = self.client.post(
            f"/admin/pages/image/{image.pk}",
            {"key": "hub", "caption": "New caption", "alt_text": "New alt", "order": 1, "published": "on"},
        )
        self.assertRedirects(response, "/admin/pages", fetch_redirect_response=False)
        image.refresh_from_db()
        self.assertEqual((image.caption, image.alt_text, image.image.name), ("New caption", "New alt", old_name))

    def test_up_and_down_swap(self):
        self.login_editor()
        first, second = list(FeatureCard.objects.all()[:2])
        self.client.post(f"/admin/pages/feature/{second.pk}/action", {"action": "up"})
        self.assertEqual(list(FeatureCard.objects.values_list("pk", flat=True)[:2]), [second.pk, first.pk])
        self.client.post(f"/admin/pages/feature/{second.pk}/action", {"action": "down"})
        self.assertEqual(list(FeatureCard.objects.values_list("pk", flat=True)[:2]), [first.pk, second.pk])

    def test_sections_move_within_their_page_and_cannot_be_deleted(self):
        self.login_editor()
        news = PageSection.objects.get(page="home", key="news")
        self.client.post(f"/admin/pages/section/{news.pk}/action", {"action": "down"})
        self.assertEqual(
            list(PageSection.objects.filter(page="home").values_list("key", flat=True)), ["download", "news"]
        )
        self.client.post(f"/admin/pages/section/{news.pk}/action", {"action": "up"})
        self.assertEqual(
            list(PageSection.objects.filter(page="home").values_list("key", flat=True)), ["news", "download"]
        )
        self.client.post(f"/admin/pages/section/{news.pk}/action", {"action": "delete"})
        self.assertTrue(PageSection.objects.filter(pk=news.pk).exists())

    def test_publish_toggle(self):
        self.login_editor()
        link = SiteLink.objects.first()
        self.client.post(f"/admin/pages/link/{link.pk}/action", {"action": "unpublish"})
        link.refresh_from_db()
        self.assertFalse(link.published)
        section = PageSection.objects.get(page="presentation", key="about")
        self.client.post(f"/admin/pages/section/{section.pk}/action", {"action": "unpublish"})
        section.refresh_from_db()
        self.assertFalse(section.enabled)
        self.assertNotContains(self.client.get("/presentation"), 'id="about"')

    def test_unknown_kind_is_404(self):
        self.login_editor()
        self.assertEqual(self.client.get("/admin/pages/nope/1").status_code, 404)
        self.assertEqual(self.client.post("/admin/pages/nope/1/action", {"action": "delete"}).status_code, 404)

    def test_settings_form_keeps_the_content_version(self):
        self.login_editor()
        start = SiteSettings.load().content_version
        data = {
            "site_name": "Owl Engine",
            "tagline": "New tagline",
            "pitch": "Pitch",
            "meta_description": "Description",
            "cta_discover_label": "Discover",
            "cta_download_label": "Download",
            "cta_docs_label": "Docs",
            "cta_github_label": "GitHub",
            "news_count": 3,
            "roadmap_teaser_count": 2,
            "footer_text": "Footer",
        }
        response = self.client.post("/admin/pages/settings", data)
        self.assertRedirects(response, "/admin/pages", fetch_redirect_response=False)
        settings_row = SiteSettings.load()
        self.assertEqual(settings_row.tagline, "New tagline")
        self.assertEqual(settings_row.content_version, start + 1)
        self.assertContains(self.client.get("/"), "New tagline")

    def test_users_toggles(self):
        admin = User.objects.create_superuser("root", "root@example.com", "secret-password")
        target = User.objects.create_user("ci", password="secret-password")
        self.client.force_login(admin)
        self.client.post(f"/admin/user/{target.pk}", {"action": "toggle_pages_push"})
        target = User.objects.get(pk=target.pk)
        self.assertTrue(all(target.has_perm(f"delivery.{code}") for code in PAGES_PUSH_CODENAMES))
        self.assertFalse(target.has_perm("delivery.change_featurecard"))
        self.client.post(f"/admin/user/{target.pk}", {"action": "toggle_pages_edit"})
        target = User.objects.get(pk=target.pk)
        self.assertTrue(target.has_perm("delivery.change_featurecard"))
        self.client.post(f"/admin/user/{target.pk}", {"action": "toggle_pages_edit"})
        target = User.objects.get(pk=target.pk)
        self.assertFalse(target.has_perm("delivery.change_featurecard"))
