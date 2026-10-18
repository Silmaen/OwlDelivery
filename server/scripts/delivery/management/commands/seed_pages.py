"""
Create the default content of the home and presentation pages.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from delivery.pages_seed import seed_pages


class Command(BaseCommand):
    help = "Create the missing default content of the home and presentation pages; existing rows are never modified."

    def add_arguments(self, parser):
        parser.add_argument("--images", default=None, help="Folder of PNG screenshots to import (keys = file stems).")

    def handle(self, *args, **options):
        with transaction.atomic():
            created = seed_pages(options["images"])
        summary = ", ".join(f"{name}: {count}" for name, count in created.items() if count) or "nothing to create"
        self.stdout.write(f"Pages seeded ({summary}).")
