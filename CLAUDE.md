# OwlDelivery

Django web application for hosting and managing the delivery packages of **Owl Engine**, with the engine's public
home page (`/`) and presentation page (`/presentation`). Runs in Docker with Nginx (reverse proxy + large file
upload) and Gunicorn. Version in `VERSION` (0.5.0, released 2026-10-18); shipped changes in `CHANGELOG.md`, planned ones in
`ROADMAP.md`.

## Quick Start

```bash
cp .env.sample .env   # configure
docker compose build   # build
docker compose up      # run
./deploy.sh            # on a server: update + build + start + health check
```

## Stack

- **Python 3.14** (Alpine Linux)
- **Django 6.x** with SQLite
- **Gunicorn** (WSGI, port 8000)
- **Nginx** (port 80, reverse proxy + upload module for large files up to 8GB)
- **django-markdownx** for Markdown editing, **nh3** to sanitize the rendered HTML
- **Pillow** for the screenshots (WebP thumbnails)
- **ruff** for linting/formatting (via Poetry dev dependency)

## Project Structure

```
OwlDelivery/
├── docker-compose.yml          # Service definition (wud label, healthcheck)
├── deploy.sh                   # Server deployment (git ff, db snapshot, build, up, health)
├── Dockerfile                  # Multi-stage build (alpine/git:v2.54.0 + python:3.14-alpine)
├── entrypoint.py               # Container init (user/perms/migrations/server start)
├── requirements.txt            # Python deps (django, pillow, gunicorn, markdownx, markdown, nh3)
├── pyproject.toml              # Dev deps (ruff) — poetry.lock is gitignored
├── .env.sample                 # Environment template
├── VERSION                     # Version number (single line)
├── CHANGELOG.md / ROADMAP.md   # Shipped / planned, one line per change
├── doc/specs/site-pages.md     # Spec of the home and presentation pages
├── server/
│   ├── config/
│   │   ├── nginx.conf                  # Main nginx config
│   │   └── http.d/Django_server.conf   # Server block (static/media/upload/proxy)
│   ├── data/
│   │   ├── static/
│   │   │   ├── css/                    # 9 CSS files (tokens, reset, base, layout,
│   │   │   │                           #   components, forms, tables, pages, utilities)
│   │   │   ├── js/                     # accordion.js, mobile-nav.js, gallery.js (lightbox),
│   │   │   │                           #   docs-frame.js (address bar follows the doc frame)
│   │   │   ├── img/                    # favicon.ico, logo_owl.png
│   │   │   └── scripts/api.py          # Python client script for pushing packages
│   │   └── templates/
│   │       ├── base.html               # Master template (header, nav, footer)
│   │       ├── includes/form_field.html # Reusable form field component
│   │       ├── delivery/               # Public + admin templates; home.html, presentation.html,
│   │       │                           #   sections/_<page>_<key>.html (one partial per section),
│   │       │                           #   includes/_packages.html (download buttons, shared), docs.html
│   │       ├── registration/           # Auth templates (login, register, profile, password)
│   │       ├── errors/                 # 400, 403, 404, 500 error pages
│   │       └── markdownx/             # Markdown widget template
│   └── scripts/                        # Django project root
│       ├── manage.py
│       ├── scripts/                    # Django settings module
│       │   ├── settings.py
│       │   ├── urls.py
│       │   └── wsgi.py
│       ├── delivery/                   # Main app: packages, news, branches, pages, API
│       │   ├── models.py               # NewsEntry, NewsComment, RevisionItemEntry, BranchEntry
│       │   ├── models_pages.py         # Page content models (SiteSettings, PageSection, ShowcaseImage, ...)
│       │   ├── signals.py              # content_version bump (cache key), image and package file clean-up
│       │   ├── markdown_utils.py       # markdownify_safe: markdown + nh3, the only markdown renderer
│       │   ├── pages_utils.py          # Block builders + per-block cache of the two pages
│       │   ├── pages_seed.py           # Default content; management/commands/seed_pages.py
│       │   ├── release_utils.py        # Latest release (highest stable version), dev build
│       │   ├── context_processors.py   # site settings, navigation, footer links
│       │   ├── views.py                # Public views + /api endpoint (path validation, nginx upload merge)
│       │   ├── views_pages.py          # Home (/), presentation, robots.txt
│       │   ├── views_docs.py           # /docs/<branch>/: site header + doxygen in a frame
│       │   ├── api_pages.py            # push_screenshot, push_release, release_info
│       │   ├── views_admin.py          # Admin CRUD views (revisions paginated: get_revision_page)
│       │   ├── views_admin_pages.py    # Admin Pages tab (generic per-kind views)
│       │   ├── sitemaps.py             # sitemap.xml
│       │   ├── views_error.py          # Error pages (400/403/404/500), registered in scripts/urls.py
│       │   ├── urls.py                 # URL routing
│       │   ├── forms.py               # NewsEntryForm, RevisionItemEntryForm, BranchEntryForm, etc.
│       │   ├── admin.py               # Django admin site registration
│       │   ├── revision_utils.py       # Revision query helpers
│       │   ├── perms_utils.py          # Permission checks
│       │   ├── db_locking.py           # DB lock for maintenance mode
│       │   └── tests/                  # Django TestCase suite
│       └── connector/                  # User auth & profiles
│           ├── views.py                # Login, register, profile, password reset
│           ├── urls.py                 # Auth URL routes
│           └── forms.py                # CustomUserCreationForm, CustomUserChangeForm
```

## Public URLs

| URL | View | Content |
|-----|------|---------|
| `/` | `views_pages.home` | Home: hero, Discover, latest release, 3 latest news |
| `/presentation` | `views_pages.presentation` | Presentation of the engine (sections from `PageSection`) |
| `/news`, `/news/<id>` | `views.news`, `views.news_details` | Paginated feed, article with comments |
| `/branches`, `/revisions/<branch>`, `/revision/<hash>` | `views` | Downloads, a branch, a revision |
| `/docs/<branch>/[<page>]` | `views_docs.docs` | Doxygen tree in a frame under the site header |
| `/robots.txt`, `/sitemap.xml` | `views_pages`, `sitemaps` | SEO |
| `/api`, `/upload` | `views.revision_api` (+ nginx) | CI pushes |

## Container Paths

| Purpose | Path |
|---------|------|
| Django project | `/app/server/scripts/` |
| SQLite DB | `/app/data/delivery.db` |
| Packages | `/app/data/packages/{branch}/{hash}/{filename}` |
| Documentation | `/app/data/documentation/{branch}/` |
| Upload temp | `/app/data/_upload/{0-9}/` (nginx spool, world-writable files; emptied after each push) |
| Page images | `/app/data/pages/gallery/` (originals), `/app/data/pages/thumbs/` (WebP) |
| Secret key | `/app/data/secret_key` (generated when `SECRET_KEY` is unset, mode 600) |
| First admin password | `/app/data/initial_admin_password` (when `ADMIN_PASSWD` is unset, mode 600) |
| Logs | `/app/data/log/` (access, gunicorn, debugging) |
| Static (collected) | `/app/staticfiles/` |
| Migrations backup | `/app/data/migrations/` |
| Maintenance lock | `/app/data/delivery.lock` |
| Nginx config | `/app/server/config/nginx.conf` |

## entrypoint.py Startup Flow

```
check_env() → check_user_exist() → check_timezone() → check_secret_key() → correct_permission()
→ do_migrations() → seed_pages() → correct_permission() → collect_static()
→ check_admin_user() → start_server() (nginx + gunicorn foreground via execvp)
```

`correct_permission()` runs twice: before migrations (so DB is writable) and after (to fix files created as root by dump_migrations).
`seed_pages` creates the missing default content of the pages and never modifies an existing row.
`check_env()` masks the values of PASSWD/PASSWORD/SECRET/KEY/TOKEN variables. `check_admin_user()` creates the
first admin with `createsuperuser --noinput` (password through `DJANGO_SUPERUSER_PASSWORD`, never on the command
line); with an empty `ADMIN_PASSWD` it generates one in `/app/data/initial_admin_password` (`admin` only warns).
Only when the database has no superuser: changing `ADMIN_PASSWD` later changes nothing. Gunicorn workers run as
PUID/PGID (`--user`/`--group`), without `--reload`.

## Deployment (`deploy.sh`)

`./deploy.sh` = git fast-forward → database snapshot → `docker pull` of the `FROM` images →
`docker compose build` → `up -d` → wait for `healthy`. Other commands: `check` (exit 10 if an
update is pending), `status`, `logs`, `stop`, `restart`, `backup`, `superuser`, `password [user]`, `shell`,
`help`; flags `--no-pull`, `--no-backup`, `--dry-run`.

Invariants, because the fleet console of `home-server-stacks` runs this file through its wake
agent: executable, committed, works with **no argument**, never reads stdin, never asks a
question, and fails rather than deploying a checkout it could not fast-forward.

Image version tracking: `web` is built locally so it exists in no registry — hence
`wud.watch: 'false'` in `docker-compose.yml` (without it wud reports a 401 on
`library/owldelivery-web:latest`). The real subjects are the `Dockerfile`'s pinned bases,
which `deploy.sh` pulls at every deployment.

Database snapshots go to `docker_data/backup/` (last 5), **outside** `PATH_DATA`: the data volume is the one
nginx publishes (whitelisted subfolders only), and a snapshot has no business sitting next to it.

Image build: the `git-info` stage reads the commit hash from `.git`. In a git worktree `.git` is a file pointing
outside the context, so pass `--build-arg GIT_REV=$(git rev-parse --short HEAD)` (otherwise the hash is "unknown").

## Key Environment Variables

- `PUID`/`PGID` - Unix user/group IDs for file ownership
- `DOMAIN_NAME` - Required for CSRF trusted origins; also sets `ALLOWED_HOSTS` and, without a port, the https
  settings (`SECURE_PROXY_SSL_HEADER`, `Secure` cookies)
- `ALLOWED_HOSTS` - Extra host names (comma separated)
- `SECRET_KEY` - Django key; else generated once in `/app/data/secret_key`
- `PORT` - Exposed port (default: 8080)
- `PATH_DATA` - Host data volume path (default: `./docker_data/data`)
- `ADMIN_NAME`/`ADMIN_PASSWD` - Initial superuser credentials
- `DEBUG_MODE`, `TZ`, `ENABLE_STAFF`, email settings (`EMAIL_HOST`, etc.)

## API Endpoint (`/api`)

POST with HTTP Basic Auth (for this request only, no session is created) or session auth. Answers are plain
text and never echo the request headers. Actions:
- `version` - Get server version
- `push` - Upload a package file (supports direct upload via `request.FILES` and nginx upload module for large files)
- `push_doc` - Upload documentation archive (.zip/.tgz), extracted per branch (supports both direct upload and nginx upload module)
- `delete` - Delete a revision item
- `push_screenshot` - Create or update a `ShowcaseImage` by `key` (new = draft, `source=ci`; admin edits kept)
- `push_release` - Create or update the `ReleaseNote` of a branch (never touches `BranchEntry.stable`)
- `release_info` - Plain-text dump of the derived release

## Client Script (`server/data/static/scripts/api.py`)

Script Python téléchargé par les clients (CI, développeurs) via `GET /api` pour publier des releases et de la documentation sur le serveur. Il est servi comme fichier statique et exécuté côté client — il ne tourne jamais sur le serveur.

- **Dépendances client** : `requests`, `requests_toolbelt` (non incluses dans `requirements.txt` car ce sont des dépendances côté client)
- **Seuil upload** : `LARGE_FILE_THRESHOLD` (100 MB) — en dessous, envoi direct à `/api` ; au-dessus, envoi à `/upload` (module upload Nginx), avec les champs répétés dans la query string
- **Sous-commandes** : `push` (paquet, ou doc avec `-t d`), `push_screenshot`, `push_release`
- **Codes de retour** : `0` = succès, `1` = erreur serveur/réseau, `2` = dépendance Python manquante
- **Logs d'erreur** : écrits dans un sous-dossier `log/` à côté du script
- **Attention** : toute modification de ce fichier affecte tous les clients qui le téléchargent — garder la rétrocompatibilité des arguments CLI

## Django Models

- **NewsEntry** - News articles with Markdown content (title, slug, author, date, content)
- **NewsComment** - Moderated comments on news (FK to NewsEntry, FK to User, active flag)
- **RevisionItemEntry** - Package files with hash/branch/name/flavor/type/date/package(FileField); deleting one
  deletes its archive (`signals.on_package_delete`)
- **BranchEntry** - Branch metadata (name, visible, stable, date)
- **NewsEntry.published** - Draft flag: hidden from `/`, `/news` and the detail page when false
- **Page content** (`models_pages.py`): `SiteSettings` (singleton `pk=1`, site texts + `content_version`),
  `PageSection` (page, key, title, intro, enabled, order), `ShowcaseImage`, `FeatureCard`, `SampleGame`,
  `RoadmapMilestone`, `ReleaseNote`, `SiteLink`. Each block of `/` and `/presentation` is cached under
  `pages:<page>:<block>:<content_version>`; signals bump the counter on every save/delete, so change these rows
  with `save()`/`delete()`, **never `QuerySet.update()`** (no signal, stale cache)
- **Seed links** (`pages_seed.link_new_image`): a new `ShowcaseImage` fills the empty fields waiting for its key —
  `hub` → hero, `social_preview` → social image, `SAMPLE_IMAGE_KEYS` → seeded sample games

## Permissions

- `auth.view_user` / `auth.delete_user` - View/manage users
- `delivery.add_newsentry` / `delivery.delete_newsentry` - Create/delete news
- `delivery.delete_newscomment` - Moderate comments
- `delivery.add_revisionitementry` / `delivery.delete_revisionitementry` - Upload/delete packages
- `delivery.change_<page model>` - Any of them opens the Pages admin tab and `?preview=1`
- `delivery.add_showcaseimage` / `delivery.add_releasenote` - CI push of screenshots / release notes
- User manager (`auth.delete_user`): never changes their own account or a superuser, and only grants or removes a
  permission they hold themselves (`USER_TOGGLES` in `views_admin.py`)
- Every admin view checks its permission, including GET; admin redirects go to fixed URL names, never `Referer`.
  The revision admin (`/admin/revisions[/<n>]?branch=`) pages `REVISION_PER_PAGE` revisions from one grouped query;
  its delete forms post `page` and `branch`, and `revisions_return_url` sends back to that page

## Frontend

- **CSS architecture**: 9 files with BEM naming (`tokens.css` → `utilities.css`)
- **Design tokens**: `tokens.css` defines colors (primary golden #be8509, neutral palette), spacing (4px scale), typography (Inter), breakpoints (480/768/1024/1280px)
- **JS**: `accordion.js` (collapsible panels with `aria-expanded`), `mobile-nav.js` (hamburger menu),
  `gallery.js` (native `<dialog>` lightbox, presentation page only)
- **Icons**: Material Symbols Outlined (Google Fonts)
- **Forms**: `INPUT_CSS = {"class": "form-group__input"}` on all widget attrs; `includes/form_field.html` template for rendering fields with label/help/errors

## Conventions

- Nginx upload module handles `/upload` path, passes to `/api` after storing file. It drops the text fields of the
  form, so `api.py` repeats them in the query string (`upload_pass_args on`) and `revision_api` merges `request.GET`
  when `package.path` is present
- `/api` validates every field that becomes a path (`branch`, `hash`, `package.name`: no `..`, no leading `/`) and
  only accepts a `package.path` inside `/app/data/_upload/`
- Documentation links go through `get_branch_documentation_url` → `/docs/<branch>/` (the site frame); the raw
  doxygen URL (`/media/documentation/<branch>/`) is only the `src` of the frame
- Content pages (news, downloads, revisions) render their own `<h1>` and pass no `title` (no page-header band)
- Markdown is always rendered with `markdown_utils.markdownify_safe` (python-markdown + nh3), never `markdownify`
  alone: the templates print it `|safe`
- FileField stores relative paths (e.g., `packages/main/abc123/file.zip`), MEDIA_ROOT is `/app/data`
- `/media` is a **whitelist** in nginx (`packages/`, `documentation/`, `markdownx/`, `pages/`), everything
  else returns 404: the data volume also holds `delivery.db`, `log/` and `_upload/`, and a bare
  `alias /app/data` published the database. Adding a public subdirectory is a deliberate edit of
  `server/config/http.d/Django_server.conf`
- Static files are collected at container start (`/app/staticfiles`): after a CSS/JS change, restart the container
- `server/VERSION` is generated at Docker build time (version + git short hash) — never commit manually
- `.gitignore` excludes `server/VERSION`, `sample_data/*`, `docker_data/`, `.env`, `poetry.lock`
- Settings: `SECRET_KEY` from `.env` or `/app/data/secret_key`; `ALLOWED_HOSTS` from `DOMAIN_NAME` (+ `ALLOWED_HOSTS`);
  a `DOMAIN_NAME` without port turns on `SECURE_PROXY_SSL_HEADER` and `Secure` cookies (TLS proxy in front)
- Lint: ruff is not in the image — run it from a throwaway `python:3.14-alpine` container
- Tests: `delivery/tests/`, run in the container
  (`docker compose run --rm --entrypoint python3 -w /app/server/scripts web manage.py test delivery`);
  under `test`, `MIGRATION_MODULES` disables migrations (they are generated at start, never committed)
- Constants in UPPER_SNAKE_CASE at module level
- Explicit imports, no wildcard imports
- `super()` without arguments (PEP 3135)
- Filenames in snake_case
