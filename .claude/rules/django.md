---
paths:
  - "server/scripts/**/*.py"
  - "requirements.txt"
---

# Django Conventions

## Stack

- **Django 6.x** on **Python 3.13** (Alpine)
- SQLite database at `/app/data/delivery.db`
- `django-markdownx` for Markdown fields
- Gunicorn as WSGI server (port 8000)

## Apps

- **delivery** — packages, revisions, branches, news, API (`/api`)
- **connector** — user auth, registration, profiles

## Models

- `FileField` values must be **relative** paths (e.g., `packages/main/abc123/file.zip`). Never store absolute paths — `MEDIA_ROOT` (`/app/data`) is prepended by Django.
- `BranchEntry.date` is auto-updated when a `RevisionItemEntry` is saved.

## Settings

- Environment-driven config: `DEBUG_MODE`, `DOMAIN_NAME`, `PORT`, `PUID`/`PGID`, email, etc.
- `STATIC_ROOT = "/app/staticfiles/"` — collected by `entrypoint.py` at startup
- `MEDIA_ROOT = "/app/data"` — served by Nginx at `/media`
- Error handlers (`handler400`..`handler500`) are defined in `settings.py`

## URL Structure

- `/` and `/news` — public news
- `/branches`, `/revisions/<branch>`, `/revision/<hash>` — public package browsing
- `/admin/*` — app admin views (not Django admin)
- `/staff/` — Django admin (only if `ENABLE_STAFF=True`)
- `/profile/*` — auth (login, register, password reset)
- `/api` — REST endpoint (push/delete/version, HTTP Basic Auth or session)
- `/upload` — handled by Nginx upload module, forwarded to `/api`

## Permissions

Use the helpers in `delivery/perms_utils.py` (`can_see_admin`, `can_see_revision_admin`, etc.) — don't check permissions manually in views.

## Redirects

Use `redirect("/")` or `redirect("url_name")` — never `redirect("HTTP_REFERER", "/")`.
