"""
Access rules of the site admin views.
"""

from django.contrib.auth.models import Permission, User
from django.test import TestCase

from delivery.models import NewsComment, NewsEntry, RevisionItemEntry


def grant(user, *codenames):
    user.user_permissions.add(*Permission.objects.filter(codename__in=codenames))
    return User.objects.get(pk=user.pk)


class AdminAccessTest(TestCase):
    def setUp(self):
        self.news = NewsEntry.objects.create(title="T", slug="t")
        self.item = RevisionItemEntry.objects.create(
            hash="aaa111", branch="0.3.0", name="Owl Engine", flavor_name="linux x64", rev_type="e", package="x.zip"
        )

    def test_admin_pages_need_a_permission(self):
        for url in (f"/admin/news/{self.news.pk}", f"/admin/erevision_item/{self.item.pk}"):
            self.assertRedirects(self.client.get(url), "/", fetch_redirect_response=False)
        self.client.force_login(User.objects.create_user("visitor", password="visitor-password"))
        for url in (f"/admin/news/{self.news.pk}", f"/admin/erevision_item/{self.item.pk}"):
            self.assertRedirects(self.client.get(url), "/", fetch_redirect_response=False)

    def test_missing_rows_are_404(self):
        admin = User.objects.create_superuser("root", "root@example.com", "root-password")
        self.client.force_login(admin)
        self.assertEqual(self.client.get("/admin/news/999").status_code, 404)
        self.assertEqual(self.client.get("/admin/erevision_item/999").status_code, 404)
        self.assertEqual(self.client.post("/admin/user/999", {"action": "delete"}).status_code, 404)

    def test_comment_actions_go_back_to_their_news(self):
        moderator = grant(User.objects.create_user("moderator", password="moderator-password"), "delete_newscomment")
        comment = NewsComment.objects.create(related_news=self.news, author=moderator, content="c")
        self.client.force_login(moderator)
        response = self.client.post(f"/admin/mcomment/{comment.pk}", {"action": "toggle_active"})
        self.assertRedirects(response, f"/admin/news/{self.news.pk}", fetch_redirect_response=False)
        comment.refresh_from_db()
        self.assertTrue(comment.active)

    def test_referer_is_never_followed(self):
        admin = User.objects.create_superuser("root", "root@example.com", "root-password")
        self.client.force_login(admin)
        response = self.client.post(
            f"/admin/mnews/{self.news.pk}", {"action": "delete"}, HTTP_REFERER="https://evil.example/"
        )
        self.assertRedirects(response, "/admin/news", fetch_redirect_response=False)


class UserManagementTest(TestCase):
    def setUp(self):
        self.manager = grant(User.objects.create_user("manager", password="manager-password"), "delete_user")
        self.other = User.objects.create_user("other", password="other-password")
        self.root = User.objects.create_superuser("root", "root@example.com", "root-password")
        self.client.force_login(self.manager)

    def post(self, user, action):
        return self.client.post(f"/admin/user/{user.pk}", {"action": action})

    def test_manager_cannot_grant_what_they_lack(self):
        self.post(self.manager, "toggle_news_add")
        self.post(self.other, "toggle_news_add")
        self.post(self.other, "toggle_pages_edit")
        self.assertFalse(User.objects.get(pk=self.manager.pk).has_perm("delivery.add_newsentry"))
        self.assertFalse(User.objects.get(pk=self.other.pk).has_perm("delivery.add_newsentry"))
        self.assertFalse(User.objects.get(pk=self.other.pk).has_perm("delivery.change_featurecard"))

    def test_manager_grants_what_they_hold(self):
        self.post(self.other, "toggle_user_delete")
        self.assertTrue(User.objects.get(pk=self.other.pk).has_perm("auth.delete_user"))

    def test_manager_cannot_touch_themselves_or_a_superuser(self):
        self.post(self.manager, "delete")
        self.post(self.root, "delete")
        self.assertTrue(User.objects.filter(pk=self.manager.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.root.pk).exists())

    def test_manager_deletes_a_regular_user(self):
        self.post(self.other, "delete")
        self.assertFalse(User.objects.filter(pk=self.other.pk).exists())

    def test_users_page_hides_the_buttons_of_protected_accounts(self):
        content = self.client.get("/admin/users").content.decode()
        self.assertIn(f'/admin/user/{self.other.pk}"', content)
        self.assertNotIn(f'/admin/user/{self.root.pk}"', content)
        self.assertNotIn(f'/admin/user/{self.manager.pk}"', content)
