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
- **ruff** for linting/formatting (via Poetry dev dependency)

## Project Structure

```
OwlDelivery/
├── docker-compose.yml          # Service definition
├── Dockerfile                  # Multi-stage build (alpine/git + python:3.13-alpine)
├── entrypoint.py               # Container init (user/perms/migrations/server start)
├── requirements.txt            # Python deps (django, pillow, gunicorn, markdownx, markdown)
├── pyproject.toml              # Dev deps (ruff) — poetry.lock is gitignored
├── .env.sample                 # Environment template
├── VERSION                     # Version number (single line)
├── server/
│   ├── config/
│   │   ├── nginx.conf                  # Main nginx config
│   │   └── http.d/Django_server.conf   # Server block (static/media/upload/proxy)
│   ├── data/
│   │   ├── static/
│   │   │   ├── css/                    # 9 CSS files (tokens, reset, base, layout,
│   │   │   │                           #   components, forms, tables, pages, utilities)
│   │   │   ├── js/                     # accordion.js, mobile-nav.js
│   │   │   ├── img/                    # favicon.ico, logo_owl.png
│   │   │   └── scripts/api.py          # Python client script for pushing packages
│   │   └── templates/
│   │       ├── base.html               # Master template (header, nav, footer)
│   │       ├── includes/form_field.html # Reusable form field component
│   │       ├── delivery/               # Public + admin templates
│   │       ├── registration/           # Auth templates (login, register, profile, password)
│   │       ├── errors/                 # 400, 403, 404, 500 error pages
│   │       └── markdownx/             # Markdown widget template
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
│       │   ├── urls.py                 # URL routing
│       │   ├── forms.py               # NewsEntryForm, RevisionItemEntryForm, BranchEntryForm, etc.
│       │   ├── admin.py               # Django admin site registration
│       │   ├── revision_utils.py       # Revision query helpers
│       │   ├── perms_utils.py          # Permission checks
│       │   └── db_locking.py           # DB lock for maintenance mode
│       └── connector/                  # User auth & profiles
│           ├── views.py                # Login, register, profile, password reset
│           ├── urls.py                 # Auth URL routes
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
| Maintenance lock | `/app/data/delivery.lock` |
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
- `push` - Upload a package file (supports direct upload via `request.FILES` and nginx upload module for large files)
- `push_doc` - Upload documentation archive (.zip/.tgz), extracted per branch (supports both direct upload and nginx upload module)
- `delete` - Delete a revision item

## Client Script (`server/data/static/scripts/api.py`)

Script Python téléchargé par les clients (CI, développeurs) via `GET /api` pour publier des releases et de la documentation sur le serveur. Il est servi comme fichier statique et exécuté côté client — il ne tourne jamais sur le serveur.

- **Dépendances client** : `requests`, `requests_toolbelt` (non incluses dans `requirements.txt` car ce sont des dépendances côté client)
- **Seuil upload** : `LARGE_FILE_THRESHOLD` (100 MB) — en dessous, envoi direct à `/api` ; au-dessus, envoi à `/upload` (module upload Nginx)
- **Codes de retour** : `0` = succès, `1` = erreur serveur/réseau, `2` = dépendance Python manquante
- **Logs d'erreur** : écrits dans un sous-dossier `log/` à côté du script
- **Attention** : toute modification de ce fichier affecte tous les clients qui le téléchargent — garder la rétrocompatibilité des arguments CLI

## Django Models

- **NewsEntry** - News articles with Markdown content (title, slug, author, date, content)
- **NewsComment** - Moderated comments on news (FK to NewsEntry, FK to User, active flag)
- **RevisionItemEntry** - Package files with hash/branch/name/flavor/type/date/package(FileField)
- **BranchEntry** - Branch metadata (name, visible, stable, date)

## Permissions

- `auth.view_user` / `auth.delete_user` - View/manage users
- `delivery.add_newsentry` / `delivery.delete_newsentry` - Create/delete news
- `delivery.delete_newscomment` - Moderate comments
- `delivery.add_revisionitementry` / `delivery.delete_revisionitementry` - Upload/delete packages

## Frontend

- **CSS architecture**: 9 files with BEM naming (`tokens.css` → `utilities.css`)
- **Design tokens**: `tokens.css` defines colors (primary golden #be8509, neutral palette), spacing (4px scale), typography (Inter), breakpoints (480/768/1024/1280px)
- **JS**: `accordion.js` (collapsible panels with `aria-expanded`), `mobile-nav.js` (hamburger menu)
- **Icons**: Material Symbols Outlined (Google Fonts)
- **Forms**: `INPUT_CSS = {"class": "form-group__input"}` on all widget attrs; `includes/form_field.html` template for rendering fields with label/help/errors

## Conventions

- Nginx upload module handles `/upload` path, passes to `/api` after storing file
- FileField stores relative paths (e.g., `packages/main/abc123/file.zip`), MEDIA_ROOT is `/app/data`
- `server/VERSION` is generated at Docker build time (version + git short hash) — never commit manually
- `.gitignore` excludes `server/VERSION`, `sample_data/*`, `docker_data/`, `.env`, `poetry.lock`
- Constants in UPPER_SNAKE_CASE at module level
- Explicit imports, no wildcard imports
- `super()` without arguments (PEP 3135)
- Filenames in snake_case
