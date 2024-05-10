"""
Fichier définissant les urls
"""

from django.conf import settings as main_settings
from django.conf.urls.static import static
from django.urls import path

from .views import *
from .views_user import *

urlpatterns = [
    path("", index, name="index"),
    path("news", index, name="news"),
    path("documentation", documentation, name="documentation"),
    path("download", download, name="download"),
    path("users", users, name="users"),
    path("user/<int:pk>", modif_user, name="modif_user"),
] + static(main_settings.MEDIA_URL, document_root=main_settings.MEDIA_ROOT)
