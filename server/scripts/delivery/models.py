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
