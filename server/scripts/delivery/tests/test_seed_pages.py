"""
Tests of the `seed_pages` command.
"""

import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command

from delivery.models_pages import (
    FeatureCard,
    PageSection,
    ReleaseNote,
    RoadmapMilestone,
    SampleGame,
    ShowcaseImage,
    SiteLink,
    SiteSettings,
)
from delivery.pages_seed import SEED_FEATURES, SEED_LINKS, SEED_MILESTONES, SEED_SAMPLES, seed_pages

from .helpers import MediaTestCase, png_bytes, png_upload

ROW_MODELS = (SiteSettings, PageSection, FeatureCard, SampleGame, RoadmapMilestone, ReleaseNote, SiteLink)


def row_counts():
    return {model.__name__: model.objects.count() for model in ROW_MODELS}


class SeedPagesTest(MediaTestCase):
    def test_empty_tables_get_the_listed_rows(self):
        seed_pages()
        self.assertEqual(
            row_counts(),
            {
                "SiteSettings": 1,
                "PageSection": 9,
                "FeatureCard": len(SEED_FEATURES),
                "SampleGame": len(SEED_SAMPLES),
                "RoadmapMilestone": len(SEED_MILESTONES),
                "ReleaseNote": 1,
                "SiteLink": len(SEED_LINKS),
            },
        )
        self.assertEqual(SiteSettings.load().site_name, "Owl Engine")
        self.assertEqual(
            list(PageSection.objects.filter(page="home").values_list("key", flat=True)), ["download", "news"]
        )
        self.assertFalse(SampleGame.objects.get(slug="bomberman").published)

    def test_second_run_changes_nothing(self):
        seed_pages()
        before = row_counts()
        version = SiteSettings.load().content_version
        created = seed_pages()
        self.assertEqual(row_counts(), before)
        self.assertEqual(sum(created.values()), 0)
        self.assertEqual(SiteSettings.load().content_version, version)

    def test_edited_row_is_not_overwritten(self):
        seed_pages()
        card = FeatureCard.objects.get(order=1)
        card.title = "Edited title"
        card.save()
        section = PageSection.objects.get(page="presentation", key="gallery")
        section.title = "Edited section"
        section.save()
        settings_row = SiteSettings.load()
        settings_row.tagline = "Edited tagline"
        settings_row.save()
        seed_pages()
        self.assertEqual(FeatureCard.objects.get(pk=card.pk).title, "Edited title")
        self.assertEqual(PageSection.objects.get(pk=section.pk).title, "Edited section")
        self.assertEqual(SiteSettings.load().tagline, "Edited tagline")

    def test_missing_section_is_added_beside_existing_ones(self):
        seed_pages()
        PageSection.objects.get(page="presentation", key="about").delete()
        seed_pages()
        self.assertTrue(PageSection.objects.filter(page="presentation", key="about").exists())
        self.assertEqual(PageSection.objects.count(), 9)

    def test_deleted_list_row_does_not_come_back(self):
        seed_pages()
        FeatureCard.objects.get(order=1).delete()
        seed_pages()
        self.assertEqual(FeatureCard.objects.count(), len(SEED_FEATURES) - 1)

    def test_images_are_imported_and_linked(self):
        with tempfile.TemporaryDirectory() as images_dir:
            for key in ("hub", "raycast", "social_preview"):
                (Path(images_dir) / f"{key}.png").write_bytes(png_bytes())
            seed_pages(images_dir)
            self.assertEqual(ShowcaseImage.objects.count(), 3)
            settings_row = SiteSettings.load()
            self.assertEqual(settings_row.hero_image.key, "hub")
            self.assertEqual(settings_row.social_image.key, "social_preview")
            self.assertFalse(ShowcaseImage.objects.get(key="social_preview").in_gallery)
            self.assertEqual(SampleGame.objects.get(slug="wolfenstein").image.key, "raycast")
            seed_pages(images_dir)
            self.assertEqual(ShowcaseImage.objects.count(), 3)

    def test_command_reports_what_it_created(self):
        out = StringIO()
        call_command("seed_pages", stdout=out)
        self.assertIn("PageSection: 9", out.getvalue())
        out = StringIO()
        call_command("seed_pages", stdout=out)
        self.assertIn("nothing to create", out.getvalue())

    def test_images_arriving_after_the_seed_reach_the_samples(self):
        seed_pages()
        wolfenstein = SampleGame.objects.get(slug="wolfenstein")
        self.assertIsNone(wolfenstein.image)
        tycoon = SampleGame.objects.get(slug="mini-transport-tycoon")
        tycoon.image = ShowcaseImage.objects.create(key="admin_choice", alt_text="Chosen", image=png_upload())
        tycoon.save()
        with tempfile.TemporaryDirectory() as images_dir:
            for key in ("raycast", "iso_town"):
                (Path(images_dir) / f"{key}.png").write_bytes(png_bytes())
            seed_pages(images_dir)
        self.assertEqual(SampleGame.objects.get(slug="wolfenstein").image.key, "raycast")
        self.assertEqual(SampleGame.objects.get(slug="mini-transport-tycoon").image.key, "admin_choice")
