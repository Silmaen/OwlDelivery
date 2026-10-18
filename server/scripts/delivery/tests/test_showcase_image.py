"""
Tests of the showcase image files: content-hashed names, thumbnails, clean-up.
"""

from pathlib import Path

from delivery.models_pages import THUMBNAIL_WIDTH, ShowcaseImage

from .helpers import MediaTestCase, png_upload


class ShowcaseImageTest(MediaTestCase):
    def make(self, key="hub", **kwargs):
        image = ShowcaseImage(key=key, alt_text="A village", image=png_upload(**kwargs))
        image.save()
        return image

    def test_name_carries_key_and_content_hash(self):
        image = self.make()
        self.assertRegex(image.image.name, r"^pages/gallery/hub-[0-9a-f]{8}\.png$")
        self.assertEqual((image.width, image.height), (1280, 720))

    def test_thumbnail_is_a_narrow_webp(self):
        image = self.make()
        self.assertTrue(image.thumbnail.name.endswith(".webp"))
        self.assertEqual(image.thumbnail.width, THUMBNAIL_WIDTH)
        self.assertEqual(image.thumbnail.height, 360)

    def test_small_image_is_not_enlarged(self):
        image = self.make(width=320, height=200)
        self.assertEqual(image.thumbnail.width, 320)

    def test_replacing_the_image_removes_the_old_files(self):
        image = self.make()
        old_paths = [Path(image.image.path), Path(image.thumbnail.path)]
        image.image = png_upload(color=(10, 20, 30))
        image.save()
        self.assertNotEqual(Path(image.image.path), old_paths[0])
        for path in old_paths:
            self.assertFalse(path.exists())
        self.assertTrue(Path(image.thumbnail.path).exists())

    def test_saving_other_fields_keeps_the_files(self):
        image = self.make()
        name = image.image.name
        image.caption = "New caption"
        image.save()
        self.assertEqual(ShowcaseImage.objects.get(pk=image.pk).image.name, name)
        self.assertTrue(Path(image.image.path).exists())

    def test_delete_removes_the_files(self):
        image = self.make()
        paths = [Path(image.image.path), Path(image.thumbnail.path)]
        image.delete()
        for path in paths:
            self.assertFalse(path.exists())
