---
paths:
  - "server/scripts/**/*.py"
  - "requirements.txt"
---

# Django Conventions

## Stack

- **Django 6.x** on **Python 3.14** (Alpine)
- SQLite database at `/app/data/delivery.db`
- `django-markdownx` for Markdown fields
- Gunicorn as WSGI server (port 8000)

## Apps

- **delivery** — packages, revisions, branches, news, API (`/api`)
- **connector** — user auth, registration, profiles

## Models

- `FileField` values must be **relative** paths (e.g., `packages/main/abc123/file.zip`). Never store absolute paths — `MEDIA_ROOT` (`/app/data`) is prepended by Django.
- `BranchEntry.date` is auto-updated when a `RevisionItemEntry` is saved.
- Rows shown on the home or presentation page (page models, news, branches, revision items) are changed with
  `save()` / `delete()` only: the signals of `delivery/signals.py` bump `SiteSettings.content_version`, the cache
  key of the pages. `QuerySet.update()` fires no signal and leaves the pages stale.

## Settings

- Environment-driven config: `DEBUG_MODE`, `DOMAIN_NAME`, `PORT`, `PUID`/`PGID`, email, etc.
- `STATIC_ROOT = "/app/staticfiles/"` — collected by `entrypoint.py` at startup
- `MEDIA_ROOT = "/app/data"` — served by Nginx at `/media`
- Error handlers (`handler400`..`handler500`) are defined in `settings.py`

## URL Structure

- `/` — home page (`views_pages.home`), `/presentation` — presentation page
- `/news` — public news (published only)
- `/robots.txt`, `/sitemap.xml`
- `/branches`, `/revisions/<branch>`, `/revision/<hash>` — public package browsing
- `/admin/*` — app admin views (not Django admin); `/admin/pages/*` edits the two pages
- `/staff/` — Django admin (only if `ENABLE_STAFF=True`)
- `/profile/*` — auth (login, register, password reset)
- `/api` — REST endpoint (push/push_doc/delete/version, push_screenshot/push_release/release_info; HTTP Basic Auth or session)
- `/upload` — handled by Nginx upload module, forwarded to `/api`

## Permissions

Use the helpers in `delivery/perms_utils.py` (`can_see_admin`, `can_see_revision_admin`, etc.) — don't check permissions manually in views.

## Redirects

Use `redirect("/")` or `redirect("url_name")` — never `redirect("HTTP_REFERER", "/")`.
