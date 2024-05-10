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
                  path("revisions", revisions, name="revisions"),
                  path("admin", admin, name="admin"),
                  path("admin/users", users, name="a_users"),
                  path("admin/user/<int:pk>", modif_user, name="modif_user"),
              ] + static(main_settings.MEDIA_URL, document_root=main_settings.MEDIA_ROOT)
