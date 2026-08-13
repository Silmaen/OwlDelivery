---
paths:
  - "server/config/**"
---

# Nginx Configuration

## File Structure

- `server/config/nginx.conf` — main config (worker processes, logging, http block)
- `server/config/http.d/Django_server.conf` — server block (locations)

## Path Prefix

All paths inside nginx configs must use the `/app/` prefix:
- Static files: `root /app/server/data`
- Media alias: one `alias` per public subdirectory of `/app/data` (see below)
- Upload store: `upload_store /app/data/_upload 1`
- Access log: `access_log /app/data/log/access.log`
- Include: `include /app/server/config/http.d/*.conf`

## `/media` is a whitelist, never `alias /app/data`

`MEDIA_ROOT` is `/app/data`, but that volume also holds `delivery.db`, `log/`,
`migrations/` and the `_upload/` spool. A single `alias /app/data` for `location /media`
therefore published the database: `GET /media/delivery.db` returned the whole SQLite file,
password hashes included. Fixed by serving only what is public, one `location` each:

| Prefix                 | Content                    | Written by                        |
|------------------------|----------------------------|-----------------------------------|
| `/media/packages/`     | the package files          | `get_upload_to` in `models.py`    |
| `/media/documentation/`| the doxygen trees, per branch | `push_doc` in `views.py`       |
| `/media/markdownx/`    | images from the MD editor  | django-markdownx                  |

`location /media/ { return 404; }` collects everything else — nginx picks the longest
matching prefix, so the three above win. It also covers `DEBUG_MODE=True`, where
`delivery/urls.py` would otherwise serve `MEDIA_ROOT` through Django.

**A new public subdirectory has to be added here on purpose.** That is the point: the
default is "not served".

## Upload Module

The `/upload` location uses `nginx-mod-http-upload` to handle large file uploads before passing to Django. The upload module:
1. Receives the file directly into `/app/data/_upload/{0-9}/`
2. Rewrites the request body with file metadata (path, name, md5, size)
3. Forwards to `/api` for Django processing
4. Cleans up on 4xx-5xx errors
