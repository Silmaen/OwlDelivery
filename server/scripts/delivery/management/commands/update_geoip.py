"""
Download the country database of the statistics: DB-IP Lite (CC BY 4.0, no account needed), refreshed monthly.
"""

import gzip
import os
import shutil
import tempfile
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import maxminddb
from django.conf import settings
from django.core.management.base import BaseCommand

GEOIP_URL = "https://download.db-ip.com/free/dbip-country-lite-{month}.mmdb.gz"
GEOIP_MAX_AGE_DAYS = 30
GEOIP_TIMEOUT = 30
# The download host (behind Cloudflare) refuses the default user agent of urllib with a 403.
GEOIP_USER_AGENT = "OwlDelivery (+https://github.com/Silmaen/OwlDelivery)"


def candidate_months(today):
    """
    This month's file, else last month's: the new one is published during the first days of the month.
    """
    previous = today.replace(day=1) - timedelta(days=1)
    return [today.strftime("%Y-%m"), previous.strftime("%Y-%m")]


def download(url, target):
    """
    Fetch and unpack one database next to `target`, check it opens, then swap it in.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": GEOIP_USER_AGENT})
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".tmp", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        try:
            with (
                urllib.request.urlopen(request, timeout=GEOIP_TIMEOUT) as response,
                gzip.GzipFile(fileobj=response) as data,
            ):
                shutil.copyfileobj(data, tmp)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise
    try:
        maxminddb.open_database(str(tmp_path)).close()
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    tmp_path.chmod(0o644)
    os.replace(tmp_path, target)


class Command(BaseCommand):
    help = "Download the DB-IP Lite country database when missing or older than a month (GEOIP_DOWNLOAD=False skips)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Download even if the database is recent.")

    def handle(self, *args, **options):
        if os.environ.get("GEOIP_DOWNLOAD", "True").lower() in ("false", "off", "no", "0"):
            self.stdout.write("GeoIP download disabled (GEOIP_DOWNLOAD).")
            return
        target = Path(settings.GEOIP_PATH)
        if target.is_file() and not options["force"]:
            age = date.today() - date.fromtimestamp(target.stat().st_mtime)
            if age.days < GEOIP_MAX_AGE_DAYS:
                self.stdout.write(f"GeoIP database up to date ({age.days} days old).")
                return
        # Never fatal: without the database the countries are only unknown.
        for month in candidate_months(date.today()):
            url = GEOIP_URL.format(month=month)
            try:
                download(url, target)
            except Exception as err:
                self.stderr.write(f"WARNING: GeoIP download failed ({url}): {err}")
                continue
            self.stdout.write(f"GeoIP database updated (DB-IP Lite {month}).")
            return
        self.stderr.write("WARNING: no GeoIP database could be downloaded, the countries stay unknown.")
