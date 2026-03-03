# OwlDelivery

Django web application for hosting and managing delivery packages for the Owl Game Engine. Runs in Docker with Nginx (reverse proxy + large file upload) and Gunicorn.

## Quick Start

```bash
cp .env.sample .env   # configure
docker compose build   # build
docker compose up      # run
```

## Stack

- **Python 3.13** (Alpine Linux)
- **Django 6.x** with SQLite
- **Gunicorn** (WSGI, port 8000)
- **Nginx** (port 80, reverse proxy + upload module for large files up to 8GB)
- **django-markdownx** for Markdown editing

## Project Structure

```
OwlDelivery/
├── docker-compose.yml          # Service definition
├── Dockerfile                  # Multi-stage build (alpine/git + python:3.13-alpine)
├── entrypoint.py               # Container init (user/perms/migrations/server start)
├── requirements.txt            # Python deps
├── .env.sample                 # Environment template
├── VERSION                     # Version number (single line)
├── server/
│   ├── config/
│   │   ├── nginx.conf                  # Main nginx config
│   │   └── http.d/Django_server.conf   # Server block (static/media/upload/proxy)
│   ├── data/
│   │   ├── static/scripts/api.py       # Python client script for pushing packages
│   │   └── templates/                  # HTML templates (base, delivery, registration, errors)
│   └── scripts/                        # Django project root
│       ├── manage.py
│       ├── scripts/                    # Django settings module
│       │   ├── settings.py
│       │   ├── urls.py
│       │   └── wsgi.py
│       ├── delivery/                   # Main app: packages, news, branches, API
│       │   ├── models.py               # NewsEntry, NewsComment, RevisionItemEntry, BranchEntry
│       │   ├── views.py                # Public views + /api endpoint
│       │   ├── views_admin.py          # Admin CRUD views
│       │   ├── views_error.py          # Custom error handlers (400/403/404/500)
│       │   ├── revision_utils.py        # Revision query helpers
│       │   ├── perms_utils.py          # Permission checks
│       │   ├── db_locking.py           # DB lock for maintenance mode
│       │   └── forms.py
│       └── connector/                  # User auth & profiles
│           ├── views.py                # Login, register, profile, password reset
│           └── forms.py                # CustomUserCreationForm, CustomUserChangeForm
```

## Container Paths

| Purpose | Path |
|---------|------|
| Django project | `/app/server/scripts/` |
| SQLite DB | `/app/data/delivery.db` |
| Packages | `/app/data/packages/{branch}/{hash}/{filename}` |
| Documentation | `/app/data/documentation/{branch}/` |
| Upload temp | `/app/data/_upload/{0-9}/` |
| Logs | `/app/data/log/` (access, gunicorn, debugging) |
| Static (collected) | `/app/staticfiles/` |
| Migrations backup | `/app/data/migrations/` |
| Nginx config | `/app/server/config/nginx.conf` |

## entrypoint.py Startup Flow

```
check_env() → check_user_exist() → check_timezone() → correct_permission()
→ do_migrations() → correct_permission() → collect_static()
→ check_admin_user() → start_server() (nginx + gunicorn foreground via execvp)
```

`correct_permission()` runs twice: before migrations (so DB is writable) and after (to fix files created as root by dump_migrations).

## Key Environment Variables

- `PUID`/`PGID` - Unix user/group IDs for file ownership
- `DOMAIN_NAME` - Required for CSRF trusted origins
- `PORT` - Exposed port (default: 8080)
- `PATH_DATA` - Host data volume path (default: `./docker_data/data`)
- `ADMIN_NAME`/`ADMIN_PASSWD` - Initial superuser credentials
- `DEBUG_MODE`, `TZ`, `ENABLE_STAFF`, email settings (`EMAIL_HOST`, etc.)

## API Endpoint (`/api`)

POST with HTTP Basic Auth or session auth. Actions:
- `version` - Get server version
- `push` - Upload a package file (supports nginx upload module for large files)
- `push_doc` - Upload documentation archive (.zip/.tgz), extracted per branch
- `delete` - Delete a revision item

## Django Models

- **NewsEntry** - News articles with Markdown content
- **NewsComment** - Moderated comments on news (FK to NewsEntry, FK to User)
- **RevisionItemEntry** - Package files with hash/branch/name/flavor/type/date
- **BranchEntry** - Branch metadata (name, visible, stable, date)

## Conventions

- Nginx upload module handles `/upload` path, passes to `/api` after storing file
- FileField stores relative paths (e.g., `packages/main/abc123/file.zip`), MEDIA_ROOT is `/app/data`
- `server/VERSION` is generated at Docker build time (version + git short hash)
- `.gitignore` excludes `server/VERSION`, `sample_data/*`, `docker_data/`
