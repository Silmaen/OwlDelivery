"""
Tests of the `content_version` counter, the cache key of both pages.
"""

from django.test import TestCase

from delivery.models import BranchEntry, NewsEntry, RevisionItemEntry
from delivery.models_pages import FeatureCard, SiteSettings, bump_content_version


def version():
    return SiteSettings.objects.get(pk=1).content_version


class ContentVersionTest(TestCase):
    def setUp(self):
        SiteSettings.load()

    def test_page_model_save_and_delete_bump_once(self):
        start = version()
        card = FeatureCard.objects.create(title="Card", body="Body")
        self.assertEqual(version(), start + 1)
        card.delete()
        self.assertEqual(version(), start + 2)

    def test_news_save_bumps(self):
        start = version()
        NewsEntry.objects.create(title="News", slug="news")
        self.assertEqual(version(), start + 1)

    def test_revision_item_save_bumps(self):
        start = version()
        RevisionItemEntry.objects.create(
            hash="abc123", branch="0.3.0", name="Owl Engine", flavor_name="linux x64", rev_type="e", package="x.zip"
        )
        # The item, then the branch it creates and dates: several bumps, never none.
        self.assertGreater(version(), start)
        self.assertTrue(BranchEntry.objects.filter(name="0.3.0").exists())

    def test_settings_save_bumps_once(self):
        start = version()
        settings_row = SiteSettings.load()
        settings_row.tagline = "Changed"
        settings_row.save()
        self.assertEqual(version(), start + 1)

    def test_stale_settings_instance_does_not_lower_the_counter(self):
        stale = SiteSettings.load()
        bump_content_version()
        bump_content_version()
        start = version()
        stale.tagline = "Changed from a stale form"
        stale.save()
        self.assertEqual(version(), start + 1)
        self.assertEqual(SiteSettings.load().tagline, "Changed from a stale form")

    def test_bump_creates_the_missing_row(self):
        SiteSettings.objects.all().delete()
        bump_content_version()
        self.assertTrue(SiteSettings.objects.filter(pk=1).exists())
