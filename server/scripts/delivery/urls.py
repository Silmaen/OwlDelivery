"""
Fichier définissant les urls
"""

from django.conf import settings as main_settings
from django.conf.urls.static import static
from django.urls import path

from .views import *
from .views_admin import *

urlpatterns = [
                  path("", news, name="index"),
                  path("news", news, name="news"),
                  path("news/<int:news_id>", news_details, name="news_detail"),
                  path("revisions", revisions, name="revisions"),
                  path("admin", admin, name="admin"),
                  path("admin/users", admin_users, name="a_users"),
                  path("admin/user/<int:pk>", admin_modif_user, name="modif_user"),
                  path("admin/news", admin_news, name="a_news"),
                  path("admin/news/<int:news_id>", admin_news_detail, name="a_news_detail"),
                  path("admin/mnews/<int:news_id>", admin_modif_news, name="a_modif_news"),
                  path(
                      "admin/mcomment/<int:comment_id>", admin_modif_comment, name="a_modif_comment"
                  ),
                  path("admin/revision", admin_revisions, name="a_revisions"),
              ] + static(main_settings.MEDIA_URL, document_root=main_settings.MEDIA_ROOT)
