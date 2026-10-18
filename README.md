# OwlDelivery

Django web application for hosting delivery packages and documentation for the [Owl Game Engine](https://github.com/Silmaen/Owl). Runs in Docker with Nginx (reverse proxy + large file upload) and Gunicorn.

## Quick Start

```bash
cp .env.sample .env     # configure environment
docker compose build    # build image
docker compose up       # run (Ctrl+C to stop)
```

The application is then available at `http://localhost:8080` (or the port configured in `.env`).

For a deployment on a server, use [`deploy.sh`](#deployment) instead: it does the
update, the build, the start and the health check in one command.

## Stack

- **Python 3.14** on Alpine Linux
- **Django 6.x** with SQLite
- **Gunicorn** (WSGI server, port 8000 internal)
- **Nginx** (port 80 internal, reverse proxy + upload module for large files up to 8GB)
- **django-markdownx** for Markdown editing

## Deployment

`deploy.sh` is the single entry point on a server: it fast-forwards the checkout, snapshots
the database, refreshes the base images, rebuilds, starts and waits for the container to
report healthy.

```bash
./deploy.sh                 # full deployment
./deploy.sh check           # is an update pending? (exit 10 = yes)
./deploy.sh --dry-run       # print what would run, execute nothing
./deploy.sh logs            # follow the logs
./deploy.sh help            # every command
```

Two details worth knowing:

- **the base images are refreshed by this script.** The application image is built locally,
  so it exists in no registry and nothing can watch it — hence `wud.watch: 'false'` in
  `docker-compose.yml`. What matters is the `FROM` tags of the `Dockerfile`, which are pinned
  on a version and therefore keep receiving their patch releases; `deploy.sh` pulls them at
  every deployment. Bumping a *minor* version is a deliberate edit of the `Dockerfile`.
- **the database is snapshotted before the deployment**, into `docker_data/backup/` (the last
  5 are kept). `entrypoint.py` runs `makemigrations` and `migrate` at every start, so a
  deployment can change the schema; the snapshot is the undo button. It lives outside the data
  volume on purpose, since nginx serves that volume at `/media`.

Run with no argument, the script is non-interactive: this is what lets the fleet console of
`home-server-stacks` offer a deploy button for this stack.

## Environment Variables

Copy `.env.sample` and adjust values. All variables are passed via the `env_file` directive in `docker-compose.yml`.

### Core

| Variable | Default | Description |
|----------|---------|-------------|
| `PUID` | `1000` | Unix user ID for file ownership |
| `PGID` | `1000` | Unix group ID for file ownership |
| `PORT` | `8080` | Host port mapped to the container |
| `PATH_DATA` | `./docker_data/data` | Host path for the persistent data volume |
| `DOMAIN_NAME` | `example.com` | Domain used for CSRF trusted origins and allowed hosts (see below) |
| `ALLOWED_HOSTS` | *(empty)* | Other host names than `DOMAIN_NAME`, comma separated (a LAN address...) |
| `SECRET_KEY` | *(empty)* | Django secret key; when empty, one is generated in `PATH_DATA/secret_key` at first start |
| `TZ` | `Europe/Paris` | Container timezone |

### Admin

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_NAME` | `admin` | Initial superuser login (ignored if an admin already exists) |
| `ADMIN_PASSWD` | *(empty)* | Initial superuser password |

When `ADMIN_PASSWD` is empty, the first admin gets a generated password,
written to `PATH_DATA/initial_admin_password` (readable by `PUID` only). Change it after the first login and delete
the file. The old sample value `admin` is still accepted, with a warning in the logs. Like before, `ADMIN_PASSWD` only
matters when the database has no admin yet: changing it later does not change the existing password. Passwords, secrets, keys and tokens of the environment are masked in the container logs.

### Email (SMTP)

| Variable | Default | Description |
|----------|---------|-------------|
| `EMAIL_HOST` | *(empty)* | SMTP server address |
| `EMAIL_PORT` | `587` | SMTP server port |
| `EMAIL_USE_TLS` | `True` | Use TLS for SMTP |
| `EMAIL_HOST_USER` | *(empty)* | SMTP login |
| `EMAIL_HOST_PASSWORD` | *(empty)* | SMTP password |

Email is required for password reset functionality.

### Options

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG_MODE` | `False` | Enable Django debug mode (development only) |
| `ENABLE_STAFF` | `False` | Enable the advanced admin section for staff users |
| `GUNICORN_WORKERS` | `4` | Number of Gunicorn worker processes |

### DOMAIN_NAME Details

This variable is **mandatory** for CSRF resolution on POST requests, and only its host (plus `localhost` and
`127.0.0.1`) is accepted in the `Host` header: add any other name with `ALLOWED_HOSTS`. A domain name without port
means the site runs behind a TLS proxy (swag): Django then trusts `X-Forwarded-Proto` and marks its cookies `Secure`.

Include the port if it is not the standard HTTP/HTTPS port:

- Access via `http://10.15.165.12:7856` → `DOMAIN_NAME=10.15.165.12:7856`
- Access via `https://deliv.home.lan:785` → `DOMAIN_NAME=deliv.home.lan:785`
- Access via `https://delivery.example.com` → `DOMAIN_NAME=delivery.example.com`

## Pages

- `/` is the home page: product name, a **Discover** link, the latest release and the 3 latest news.
- `/presentation` presents the engine: screenshots, features, downloads per platform, sample games, roadmap.
- Every text, image and list of both pages is a database row, edited in **Admin → Pages** (preview with
  `?preview=1`) or pushed by the engine CI; nothing needs a redeploy. The default content is created at start by
  `manage.py seed_pages`, which never modifies an existing row.
- The latest release is the visible stable branch with the highest `MAJOR.MINOR.PATCH`.
- `/docs/<branch>/` shows the doxygen documentation under the site header; `/news` and `/branches` list the news and
  the downloads.

Design and rules: [doc/specs/site-pages.md](doc/specs/site-pages.md).

## Client Script (api.py)

A Python script is served at `GET /api` for CI systems and developers to publish releases and documentation.

```bash
# Download the script
curl -o api.py http://your-server/api

# Push a package
python api.py push --url http://your-server --user admin --passwd secret \
    --type e --name "Owl Engine" --hash abc123 --branch 0.3.0 --date 2026-10-11T12:00:00 \
    --flavor_name "linux glibc_2.43 x64" --file package.tar.gz

# Push documentation (a folder holding index.html, archived by the script)
python api.py push --url http://your-server --user admin --passwd secret \
    --type d --branch 0.3.0 --file doc/html

# Push a screenshot of the presentation page (a new key is a draft unless --publish)
python api.py push_screenshot --url http://your-server --user ci --passwd secret \
    --key raycast --file raycast.png --caption "Raycast level" --style_tag raycast

# Push the release note of a version
python api.py push_release --url http://your-server --user ci --passwd secret \
    --branch 0.3.0 --title "Owl Engine 0.3.0" --release_date 2026-10-11 --highlights_file highlights.md
```

**Client dependencies**: `requests`, `requests_toolbelt` (install with `pip install requests requests_toolbelt`).

**Exit codes**: `0` = success, `1` = server/network error, `2` = missing Python dependency.

Files under 100 MB are uploaded directly to `/api`; larger files use the Nginx upload module at `/upload`, with the
fields also in the query string (the module drops the text fields of the form). Download a fresh `api.py`: older
copies cannot push files above 100 MB.

## API Endpoint (`/api`)

POST with HTTP Basic Auth or session authentication. Actions:

| Action | Permission | Description |
|--------|------------|-------------|
| `version` | authenticated | Get server version |
| `push` | `add_revisionitementry` | Upload a package file |
| `push_doc` | `add_revisionitementry` | Upload documentation archive (.zip/.tgz), extracted per branch |
| `delete` | `delete_revisionitementry` | Delete a revision item |
| `push_screenshot` | `add_showcaseimage` | Create or update a screenshot by `key`; admin edits are kept |
| `push_release` | `add_releasenote` | Create or update the release note of a `branch` |
| `release_info` | authenticated | Plain-text dump of the release the pages offer |

GET returns the client script (`api.py`). The **Pages push** toggle of Admin → Users grants the two
permissions of the CI.

## Project Structure

```
OwlDelivery/
├── docker-compose.yml          # Service definition (wud label, healthcheck)
├── deploy.sh                   # Server deployment (update, backup, build, start, health)
├── Dockerfile                  # Multi-stage build (alpine/git + python:3.14-alpine)
├── entrypoint.py               # Container init (user/perms/migrations/server start)
├── requirements.txt            # Python deps (django, pillow, gunicorn, markdownx, markdown)
├── pyproject.toml              # Dev deps (ruff via Poetry)
├── .env.sample                 # Environment template
├── VERSION                     # Version number
├── CHANGELOG.md / ROADMAP.md   # What shipped / what is planned
├── doc/specs/                  # Design specifications
├── server/
│   ├── config/
│   │   ├── nginx.conf                  # Main Nginx config
│   │   └── http.d/Django_server.conf   # Server block (static/media/upload/proxy)
│   ├── data/
│   │   ├── static/                     # CSS, JS (accordion, mobile nav, gallery), images, client script
│   │   └── templates/                  # HTML templates (delivery/sections/: blocks of the two pages)
│   └── scripts/                        # Django project root
│       ├── manage.py
│       ├── scripts/                    # Django settings module
│       ├── delivery/                   # Main app: packages, news, branches, pages, API (tests/ inside)
│       └── connector/                  # User auth & profiles
```

## Tests

The Django tests run inside the container, on an in-memory database built from the models:

```bash
docker compose run --rm --entrypoint python3 -w /app/server/scripts web manage.py test delivery
```

## Changelog and roadmap

Shipped changes are listed in [CHANGELOG.md](CHANGELOG.md), planned ones in [ROADMAP.md](ROADMAP.md).
