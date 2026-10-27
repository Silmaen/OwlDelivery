"""
Delete the traffic hits older than the retention period, or the robot hits that have no name.
"""

from django.core.management.base import BaseCommand

from delivery.stats_utils import STATS_RETENTION_DAYS, purge_old_hits, purge_unnamed_robots


class Command(BaseCommand):
    help = f"Delete the page views and downloads older than {STATS_RETENTION_DAYS} days."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=STATS_RETENTION_DAYS, help="Retention, in days.")
        parser.add_argument(
            "--unnamed-robots",
            action="store_true",
            help="Delete instead the robot hits recorded before the robots were named.",
        )

    def handle(self, *args, **options):
        if options["unnamed_robots"]:
            deleted = purge_unnamed_robots()
            self.stdout.write(f"Statistics purged ({deleted} unnamed robot hit{'s' if deleted != 1 else ''}).")
            return
        deleted = purge_old_hits(options["days"])
        self.stdout.write(
            f"Statistics purged ({deleted} hit{'s' if deleted != 1 else ''} older than {options['days']} days)."
        )
