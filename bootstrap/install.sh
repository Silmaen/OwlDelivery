#!/usr/bin/env sh

set -e

apk add --no-cache tzdata
apk add --no-cache nginx nginx-mod-http-upload nginx-mod-stream nginx-mod-http-upload-progress nginx-mod-http-encrypted-session
apk add --no-cache python3 py3-django py3-pillow py3-gunicorn py3-pip
pip install django-markdownx --break-system-packages
ln -s /usr/lib/python3.11/site-packages/markdownx/templates/markdownx /usr/lib/python3.11/site-packages/django/forms/templates/markdownx
chmod 777 -R /server
chmod 777 /bootstrap/start.py
