"""
Deleting a revision item deletes its archive.
"""

from pathlib import Path

from .helpers import MediaTestCase, make_item


class PackageFilesTest(MediaTestCase):
    def test_delete_removes_the_file_and_empty_folders(self):
        first = make_item("0.3.0", "aaa111")
        second = make_item("0.3.0", "aaa111", flavor="windows x64")
        first_path, second_path = Path(first.package.path), Path(second.package.path)
        first.delete()
        self.assertFalse(first_path.exists())
        self.assertTrue(second_path.exists())
        second.delete()
        self.assertFalse((Path(self.media_root) / "packages" / "0.3.0").exists())
        self.assertTrue((Path(self.media_root) / "packages").exists())

    def test_missing_file_is_not_an_error(self):
        make_item("0.3.0", "aaa111", with_file=False).delete()
