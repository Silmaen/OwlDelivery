"""
Tests of the presentation page (`/presentation`).
"""

import re
import tempfile
from pathlib import Path

from delivery.models_pages import PageSection, RoadmapMilestone, SampleGame
from delivery.pages_seed import seed_pages

from .helpers import PagesTestCase, make_item, png_bytes


def section_ids(response):
    return re.findall(r'<section class="page-section[^"]*" id="([a-z]+)"', response.content.decode())


class PresentationViewTest(PagesTestCase):
    def test_renders_with_an_empty_database(self):
        response = self.client.get("/presentation")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<h1", count=1)
        self.assertContains(response, "page-hero__placeholder")
        self.assertEqual(section_ids(response), [])

    def test_renders_a_full_seed(self):
        seed_pages()
        response = self.client.get("/presentation")
        self.assertEqual(section_ids(response), ["features", "release", "samples", "roadmap", "about", "links"])
        self.assertContains(response, "<h1", count=1)
        self.assertContains(response, "No release yet")
        self.assertContains(response, "Render-style mixing")
        self.assertContains(response, "Claude Code")

    def test_gallery_appears_with_images(self):
        with tempfile.TemporaryDirectory() as images_dir:
            for key in ("hub", "raycast"):
                (Path(images_dir) / f"{key}.png").write_bytes(png_bytes())
            seed_pages(images_dir)
        response = self.client.get("/presentation")
        self.assertEqual(section_ids(response)[0], "gallery")
        self.assertContains(response, "data-gallery-item", count=2)
        self.assertContains(response, "js/gallery.js")
        self.assertContains(response, 'fetchpriority="high"')

    def test_release_with_packages(self):
        seed_pages()
        make_item("0.3.0", "aaa111", stable=True)
        make_item("0.3.0", "aaa111", flavor="windows x64")
        make_item("0.4.0", "bbb222")
        response = self.client.get("/presentation")
        self.assertContains(response, 'id="release"')
        self.assertContains(response, "Owl Engine 0.3.0 — Foundations")
        self.assertContains(response, "Owl Engine — Linux x64")
        self.assertContains(response, "Owl Engine — Windows x64")
        self.assertContains(response, "glibc_2.43 · zip · 2.00 KB")
        self.assertContains(response, "Development build, not a release")
        self.assertContains(response, 'href="/revisions/0.3.0"')

    def test_drafts_only_in_preview_for_an_editor(self):
        seed_pages()
        self.assertNotContains(self.client.get("/presentation"), "Networked Bomberman")
        self.assertNotContains(self.client.get("/presentation?preview=1"), "Networked Bomberman")
        self.client.force_login(self.make_editor())
        response = self.client.get("/presentation?preview=1")
        self.assertContains(response, "Networked Bomberman")
        self.assertContains(response, "is-draft")

    def test_disabled_section_is_absent(self):
        seed_pages()
        PageSection.objects.filter(page="presentation", key="features").update(enabled=False)
        self.assertNotIn("features", section_ids(self.client.get("/presentation")))

    def test_section_order_follows_order(self):
        seed_pages()
        PageSection.objects.filter(page="presentation", key="about").update(order=0)
        self.assertEqual(section_ids(self.client.get("/presentation"))[0], "about")

    def roadmap_versions(self):
        content = self.client.get("/presentation").content.decode()
        block = re.search(r'<ol class="pres-roadmap">(.*?)</ol>', content, re.S).group(1)
        return re.findall(r"v(\d+\.\d+\.\d+)\s*<span", block)

    def test_roadmap_shows_current_teasers_and_target(self):
        seed_pages()
        self.assertEqual(self.roadmap_versions(), ["0.4.0", "0.5.0", "0.6.0", "1.0.0"])
        # save(), not update(): the signals that refresh the cache only see saves.
        milestone = RoadmapMilestone.objects.get(version="0.4.0")
        milestone.status = "released"
        milestone.save()
        self.assertEqual(self.roadmap_versions(), ["0.5.0", "0.6.0", "0.7.0", "1.0.0"])

    def test_sample_badges(self):
        seed_pages()
        response = self.client.get("/presentation")
        self.assertContains(response, "Playable, ships in v0.4.0")
        self.assertContains(response, "Planned for v0.5.0")
        self.assertEqual(SampleGame.objects.filter(published=True).count(), 5)

    def test_active_tab(self):
        response = self.client.get("/presentation")
        self.assertContains(response, 'href="/presentation" aria-current="page"')
