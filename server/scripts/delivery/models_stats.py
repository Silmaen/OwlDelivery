"""
Traffic of the site: one row per page view and per package download.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

HIT_PAGE = "p"
HIT_DOWNLOAD = "d"
HIT_KIND_CHOICES = ((HIT_PAGE, "page view"), (HIT_DOWNLOAD, "download"))


class TrafficHit(models.Model):
    """
    A page view or a download. No IP address is kept: `visitor` is a keyed hash of the address and the
    user agent that changes every day, enough to count the visitors of a day and nothing more.
    The audience (admin, service account) is read from `user` at query time, so marking an account
    as a service account also removes its past hits from the statistics.
    """

    kind = models.CharField(max_length=1, choices=HIT_KIND_CHOICES, verbose_name="Kind")
    date = models.DateTimeField(default=timezone.now, verbose_name="Date")
    path = models.CharField(max_length=255, verbose_name="Path")
    item = models.ForeignKey(
        "delivery.RevisionItemEntry",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="hits",
        verbose_name="Downloaded package",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="traffic_hits",
        verbose_name="User",
    )
    automated = models.BooleanField(default=False, verbose_name="Robot or script")
    visitor = models.CharField(max_length=16, blank=True, default="", verbose_name="Daily visitor hash")
    country = models.CharField(max_length=2, blank=True, default="", verbose_name="Country code")
    region = models.CharField(max_length=100, blank=True, default="", verbose_name="Region")
    city = models.CharField(max_length=100, blank=True, default="", verbose_name="City")
    network = models.CharField(max_length=100, blank=True, default="", verbose_name="Network (ISP, organisation)")
    agent = models.CharField(max_length=64, blank=True, default="", verbose_name="Robot or script name")
    referrer = models.CharField(max_length=255, blank=True, default="", verbose_name="Referring site")

    class Meta:
        verbose_name = "Traffic hit"
        ordering = ["-date"]
        indexes = [models.Index(fields=["kind", "date"])]

    def __str__(self):
        return f"{self.get_kind_display()} {self.path}"
