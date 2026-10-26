"""URL configuration for the delivery app."""

from django.conf import settings as main_settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.urls import path

from .sitemaps import SITEMAPS
from .views import (
    admin,
    branches,
    dl_script,
    news,
    news_details,
    revision_api,
    revision_detail,
    revisions,
)
from .views_admin import (
    admin_branches,
    admin_edit_revision_item,
    admin_modif_comment,
    admin_modif_news,
    admin_modif_revision,
    admin_modif_revision_item,
    admin_modif_user,
    admin_news,
    admin_news_detail,
    admin_revisions,
    admin_revisions_page,
    admin_users,
)
from .views_admin_pages import admin_pages, admin_pages_action, admin_pages_detail, admin_pages_settings
from .views_docs import docs
from .views_pages import home, presentation, robots_txt
from .views_stats import admin_stats, stats_download

urlpatterns = [
    path("", home, name="index"),
    path("presentation", presentation, name="presentation"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("docs/<str:branch>/", docs, name="docs"),
    path("docs/<str:branch>/<path:page>", docs, name="docs_page"),
    path("news", news, name="news"),
    path("news/<int:news_id>", news_details, name="news_detail"),
    path("branches", branches, name="branches"),
    path("revisions/<str:rev_branch>", revisions, name="revisions"),
    path("revision/<str:rev_hash>", revision_detail, name="revision_detail"),
    path("admin", admin, name="admin"),
    path("admin/users", admin_users, name="a_users"),
    path("admin/user/<int:pk>", admin_modif_user, name="modif_user"),
    path("admin/news", admin_news, name="a_news"),
    path("admin/news/<int:news_id>", admin_news_detail, name="a_news_detail"),
    path("admin/mnews/<int:news_id>", admin_modif_news, name="a_modif_news"),
    path("admin/mcomment/<int:comment_id>", admin_modif_comment, name="a_modif_comment"),
    path("admin/pages", admin_pages, name="a_pages"),
    path("admin/pages/settings", admin_pages_settings, name="a_pages_settings"),
    path("admin/pages/<str:kind>/<int:pk>", admin_pages_detail, name="a_pages_detail"),
    path("admin/pages/<str:kind>/<int:pk>/action", admin_pages_action, name="a_pages_action"),
    path("admin/stats", admin_stats, name="a_stats"),
    path("admin/revisions", admin_revisions, name="a_revisions"),
    path("admin/branches", admin_branches, name="a_branches"),
    path("admin/revisions/<int:page>", admin_revisions_page, name="a_revisions_page"),
    path(
        "admin/mrevision/<str:rev_hash>",
        admin_modif_revision,
        name="a_modif_revision",
    ),
    path(
        "admin/mrevision_item/<int:pk>",
        admin_modif_revision_item,
        name="a_modif_revision_item",
    ),
    path(
        "admin/erevision_item/<int:pk>",
        admin_edit_revision_item,
        name="a_edit_revision_item",
    ),
    path("script_api", dl_script, name="dl_script"),
    path("api", revision_api, name="rev_api"),
    # Reached only through the nginx mirror of /media/packages/ (internal location, 404 from outside).
    path("_stats/download", stats_download, name="stats_download"),
] + static(main_settings.MEDIA_URL, document_root=main_settings.MEDIA_ROOT)
