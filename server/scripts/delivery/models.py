from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import Truncator
from markdownx.models import MarkdownxField
from markdownx.utils import markdownify

truncation = 200  # Length of truncate text.
comment_truncation = 100  # Length of truncated comment.
nb_last_comments = 3  # Truncate mode number of comments to display.


class NewsEntry(models.Model):
    """
    Class for the news.
    """

    title = models.CharField(max_length=100, verbose_name="News title")
    slug = models.SlugField(max_length=100, verbose_name="News slug")
    author = models.CharField(
        max_length=50, default="admin", verbose_name="The news author"
    )
    date = models.DateTimeField(default=timezone.now, verbose_name="News date")
    content = MarkdownxField(blank=True, default="", verbose_name="Content of the news")

    class Meta:
        """
        Metadata for the news
        """

        verbose_name = "News article"
        ordering = ["-date"]

    def content_md(self):
        """
        Truncate render of markdown content.
        :return: Html output.
        """
        return Truncator(markdownify(str(self.content))).chars(
            truncation, truncate="...", html=True
        )

    def content_all_md(self):
        """
        Full render of markdown content.
        :return: Html output.
        """
        return markdownify(str(self.content))

    def nb_comments(self):
        """
        Get related comment's count.
        :return: Comment's count.
        """
        return len(self.get_all_active_comments())

    def get_comments(self):
        """
        Get the `nb_last_comments` last comments.
        :return: The `nb_last_comments` last comments.
        """
        return self.get_all_active_comments()[:nb_last_comments]

    def get_all_active_comments(self):
        """
        Get all active comments.
        :return: All active comments.
        """
        return self.comments.filter(active=True).order_by("-date")

    def get_all_comments(self):
        """
        Get all comments.
        :return: All comments.
        """
        return self.comments.order_by("-date")

    def __str__(self):
        return self.title


class NewsComment(models.Model):
    """
    Comment object.
    """

    related_news = models.ForeignKey(
        NewsEntry,
        on_delete=models.CASCADE,
        verbose_name="Linked news",
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        editable=False,
        on_delete=models.CASCADE,
        verbose_name="Comment author",
    )
    content = MarkdownxField(
        blank=True, default="", verbose_name="Markdown content of the comment"
    )
    date = models.DateTimeField(default=timezone.now, verbose_name="Comment date")
    active = models.BooleanField(default=False)

    def content_md(self):
        """
        Truncated render of markdown content.
        :return: Html output.
        """
        return Truncator(markdownify(str(self.content))).chars(
            comment_truncation, truncate="...", html=True
        )

    def content_all_md(self):
        """
        full render of markdown content.
        :return: Html output.
        """
        return markdownify(str(self.content))

    class Meta:
        """
        Meta data
        """

        verbose_name = "News comment"
        ordering = ["-date"]

    def __str__(self):
        return str(self.author) + "_" + str(self.date)


def get_upload_to(instance, filename):
    return f"packages/{instance.branch}/{instance.hash}/{filename}"


RevType = (("d", "doc"), ("e", "engine"), ("a", "application"))


class RevisionItemEntry(models.Model):
    """
    Model for a file entry
    """

    hash = models.CharField(max_length=12, verbose_name="Revision hash")
    branch = models.CharField(
        max_length=50, default="main", verbose_name="Revision branch"
    )
    name = models.CharField(max_length=50, verbose_name="Revision name", default="")
    flavor_name = models.CharField(
        max_length=50, verbose_name="Revision's flavor name", default=""
    )
    date = models.DateTimeField(default=timezone.now, verbose_name="date of build")
    rev_type = models.CharField(
        max_length=1, choices=RevType, verbose_name="Type of item"
    )
    package = models.FileField(upload_to=get_upload_to, verbose_name="Package file")

    class Meta:
        """
        Metadata for the revision item.
        """

        verbose_name = "Revision item"
        ordering = ["-date"]

    def get_pretty_size_display(self):
        """

        :return:
        """
        if not Path(self.package.path).exists():
            return f"(void)"
        raw_size = Path(self.package.path).stat().st_size
        for unite in ["", "K", "M", "G", "T"]:
            if raw_size < 1024.0:
                break
            raw_size /= 1024.0
        return f"{raw_size:.2f} {unite}"

    def get_pretty_type(self):
        if self.rev_type == "d":
            return "doc"
        elif self.rev_type == "e":
            return "engine"
        elif self.rev_type == "a":
            return "application"
