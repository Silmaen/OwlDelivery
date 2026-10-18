"""
Tests of the meta data of the pages: OpenGraph, canonical URL, JSON-LD, robots and sitemap.
"""

import json
import re
import tempfile
from pathlib import Path

from delivery.pages_seed import seed_pages

from .helpers import PagesTestCase, make_item, png_bytes


def json_ld(response):
    match = re.search(r'<script type="application/ld\+json">(.*?)</script>', response.content.decode(), re.S)
    return json.loads(match.group(1))


class PagesMetaTest(PagesTestCase):
    def test_home_meta(self):
        seed_pages()
        response = self.client.get("/")
        self.assertContains(response, '<html lang="en">')
        self.assertContains(response, "<title>Owl Engine — One engine, every rendering style</title>")
        self.assertContains(response, '<link rel="canonical" href="http://testserver/">')
        self.assertContains(response, '<meta property="og:title" content="Owl Engine">')
        self.assertContains(response, 'content="http://testserver/static/img/logo_owl.png"')
        self.assertContains(response, '<meta name="twitter:card" content="summary_large_image">')
        self.assertNotContains(response, "application/ld+json")

    def test_presentation_meta_and_json_ld(self):
        seed_pages()
        make_item("0.3.0", "aaa111", stable=True)
        response = self.client.get("/presentation")
        self.assertContains(response, "<title>Presentation — Owl Engine</title>")
        self.assertContains(response, '<link rel="canonical" href="http://testserver/presentation">')
        data = json_ld(response)
        self.assertEqual(data["@type"], "SoftwareApplication")
        self.assertEqual(data["softwareVersion"], "0.3.0")
        self.assertEqual(data["downloadUrl"], "http://testserver/revisions/0.3.0")
        self.assertEqual(data["codeRepository"], "https://github.com/Silmaen/Owl")

    def test_social_image(self):
        with tempfile.TemporaryDirectory() as images_dir:
            (Path(images_dir) / "social_preview.png").write_bytes(png_bytes(1280, 640))
            seed_pages(images_dir)
        response = self.client.get("/")
        self.assertRegex(
            response.content.decode(),
            r'<meta property="og:image" content="http://testserver/media/pages/gallery/social_preview-[0-9a-f]{8}\.png">',
        )
        self.assertContains(response, '<meta property="og:image:width" content="1280">')

    def test_site_name_everywhere(self):
        seed_pages()
        response = self.client.get("/news")
        self.assertContains(response, "<title>News — Owl Engine</title>")
        self.assertNotContains(response, "Owl Game Engine")
        self.assertContains(response, "© Argawaen — Owl Engine is MIT licensed.")
        self.assertContains(response, 'href="https://github.com/Silmaen/OwlDelivery"')
        self.assertContains(response, "Skip to content")

    def test_robots_and_sitemap(self):
        seed_pages()
        robots = self.client.get("/robots.txt")
        self.assertContains(robots, "Sitemap: http://testserver/sitemap.xml")
        sitemap = self.client.get("/sitemap.xml")
        self.assertContains(sitemap, "<loc>http://testserver/presentation</loc>")
        self.assertContains(sitemap, "<loc>http://testserver/</loc>")
