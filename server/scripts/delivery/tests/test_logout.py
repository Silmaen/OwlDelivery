"""
The logout button of the header.
"""

from django.contrib.auth.models import User
from django.test import TestCase


class LogoutTest(TestCase):
    def test_header_logs_out_with_a_post_form(self):
        User.objects.create_user("visitor", password="visitor-password")
        self.client.login(username="visitor", password="visitor-password")
        response = self.client.get("/news")
        self.assertContains(response, 'action="/profile/logout/"')
        self.assertNotContains(response, 'href="/profile/logout/"')
        response = self.client.post("/profile/logout/")
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)
