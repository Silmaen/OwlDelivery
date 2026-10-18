"""
Tests of the derived release (`release_utils`).
"""

from datetime import date
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from delivery.models import BranchEntry
from delivery.models_pages import ReleaseNote
from delivery.release_utils import (
    flavor_label,
    get_dev_build,
    get_latest_release,
    parse_version,
    release_info_text,
)

from .helpers import MediaTestCase, make_item


class ParsingTest(SimpleTestCase):
    def test_parse_version(self):
        self.assertEqual(parse_version("0.10.0"), (0, 10, 0))
        self.assertEqual(parse_version("v1.0.0"), (1, 0, 0))
        self.assertIsNone(parse_version("main"))
        self.assertIsNone(parse_version("0.4"))

    def test_flavor_label(self):
        self.assertEqual(flavor_label("linux glibc_2.43 x64"), ("Linux x64", "glibc_2.43"))
        self.assertEqual(flavor_label("linux arm64"), ("Linux arm64", ""))
        self.assertEqual(flavor_label("windows x64"), ("Windows x64", ""))
        self.assertEqual(flavor_label("windows"), ("Windows", ""))
        self.assertEqual(flavor_label(""), ("Download", ""))


class LatestReleaseTest(MediaTestCase):
    def test_no_branch_no_release(self):
        self.assertIsNone(get_latest_release())
        self.assertEqual(release_info_text(), "release: none\n")

    def test_highest_stable_version_wins_over_newer_date(self):
        make_item("0.10.0", "aaa111", stable=True)
        make_item("0.9.0", "bbb222", stable=True)
        self.assertEqual(get_latest_release()["version"], "0.10.0")

    def test_names_that_do_not_parse_sort_last(self):
        make_item("0.3.0", "aaa111", stable=True)
        make_item("release-candidate", "bbb222", stable=True)
        self.assertEqual(get_latest_release()["version"], "0.3.0")

    def test_invisible_branch_is_ignored(self):
        make_item("0.3.0", "aaa111", stable=True)
        make_item("0.4.0", "bbb222", stable=True)
        BranchEntry.objects.filter(name="0.4.0").update(visible=False)
        self.assertEqual(get_latest_release()["version"], "0.3.0")

    def test_newest_hash_and_its_packages(self):
        make_item("0.3.0", "old000", stable=True)
        make_item("0.3.0", "new111", flavor="linux glibc_2.43 x64")
        make_item("0.3.0", "new111", flavor="windows x64")
        make_item("0.3.0", "new111", name="Owl Nest", flavor="linux arm64")
        release = get_latest_release()
        self.assertEqual(release["hash"], "new111")
        self.assertEqual([package["name"] for package in release["packages"]], ["Owl Engine", "Owl Nest"])
        engine = release["packages"][0]["flavors"]
        self.assertEqual([flavor["label"] for flavor in engine], ["Linux x64", "Windows x64"])
        self.assertEqual(engine[0]["detail"], "glibc_2.43")
        self.assertEqual(engine[0]["size"], "2.00 KB")
        self.assertEqual(release["packages"][1]["flavors"][0]["label"], "Linux arm64")

    def test_missing_file_shows_void(self):
        make_item("0.3.0", "aaa111", stable=True, with_file=False)
        with self.assertLogs("delivery.release_utils", "WARNING"):
            release = get_latest_release()
        self.assertEqual(release["packages"][0]["flavors"][0]["size"], "(void)")

    def test_docs_link_only_when_the_folder_exists(self):
        make_item("0.3.0", "aaa111", stable=True)
        self.assertEqual(get_latest_release()["doc_url"], "")
        (Path(settings.MEDIA_ROOT) / "documentation" / "0.3.0").mkdir(parents=True)
        self.assertEqual(get_latest_release()["doc_url"], "/docs/0.3.0/")

    def test_release_note_date_overrides_the_build_date(self):
        make_item("0.3.0", "aaa111", stable=True)
        self.assertNotEqual(get_latest_release()["date"], date(2026, 10, 11))
        ReleaseNote.objects.create(branch="0.3.0", title="Foundations", release_date=date(2026, 10, 11))
        release = get_latest_release()
        self.assertEqual(release["date"], date(2026, 10, 11))
        self.assertEqual(release["note"].title, "Foundations")

    def test_draft_release_note_only_in_preview(self):
        make_item("0.3.0", "aaa111", stable=True)
        ReleaseNote.objects.create(branch="0.3.0", title="Draft", published=False)
        self.assertIsNone(get_latest_release()["note"])
        self.assertEqual(get_latest_release(include_drafts=True)["note"].title, "Draft")

    def test_release_info_text(self):
        make_item("0.3.0", "aaa111", stable=True)
        text = release_info_text()
        self.assertIn("release: 0.3.0", text)
        self.assertIn("package: Owl Engine | linux glibc_2.43 x64 | 2.00 KB", text)


class DevBuildTest(MediaTestCase):
    def test_dev_build_above_the_release(self):
        make_item("0.3.0", "aaa111", stable=True)
        make_item("0.4.0", "bbb222")
        release = get_latest_release()
        dev_build = get_dev_build(release)
        self.assertEqual(dev_build["version"], "0.4.0")
        self.assertEqual(dev_build["url"], "/revision/bbb222")

    def test_no_dev_build_below_the_release(self):
        make_item("0.2.0", "aaa111")
        make_item("0.3.0", "bbb222", stable=True)
        make_item("main", "ccc333")
        self.assertIsNone(get_dev_build(get_latest_release()))

    def test_dev_build_alone_without_release(self):
        make_item("0.4.0", "bbb222")
        self.assertIsNone(get_latest_release())
        self.assertEqual(get_dev_build(None)["version"], "0.4.0")
