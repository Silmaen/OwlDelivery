"""
Delete the traffic hits older than the retention period.
"""

from django.core.management.base import BaseCommand

from delivery.stats_utils import STATS_RETENTION_DAYS, purge_old_hits


class Command(BaseCommand):
    help = f"Delete the page views and downloads older than {STATS_RETENTION_DAYS} days."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=STATS_RETENTION_DAYS, help="Retention, in days.")

    def handle(self, *args, **options):
        deleted = purge_old_hits(options["days"])
        self.stdout.write(
            f"Statistics purged ({deleted} hit{'s' if deleted != 1 else ''} older than {options['days']} days)."
        )
