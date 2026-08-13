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
| `DOMAIN_NAME` | `example.com` | Domain used for CSRF trusted origins (see below) |
| `TZ` | `Europe/Paris` | Container timezone |

### Admin

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_NAME` | `admin` | Initial superuser login (ignored if an admin already exists) |
| `ADMIN_PASSWD` | `admin` | Initial superuser password |

After the first run, it is strongly recommended to change this password.

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

This variable is **mandatory** for CSRF resolution on POST requests. `127.0.0.1` and `localhost` are always trusted.

Include the port if it is not the standard HTTP/HTTPS port:

- Access via `http://10.15.165.12:7856` → `DOMAIN_NAME=10.15.165.12:7856`
- Access via `https://deliv.home.lan:785` → `DOMAIN_NAME=deliv.home.lan:785`
- Access via `https://delivery.example.com` → `DOMAIN_NAME=delivery.example.com`

## Client Script (api.py)

A Python script is served at `GET /api` for CI systems and developers to publish releases and documentation.

```bash
# Download the script
curl -o api.py http://your-server/api

# Push a package
python api.py push --server http://your-server --user admin --passwd secret \
    --name MyPackage --hash abc123 --branch main --date 2025-01-01 \
    --rev_type Release --flavor_name default --file package.zip

# Push documentation
python api.py push_doc --server http://your-server --user admin --passwd secret \
    --branch main --file docs.tgz
```

**Client dependencies**: `requests`, `requests_toolbelt` (install with `pip install requests requests_toolbelt`).

**Exit codes**: `0` = success, `1` = server/network error, `2` = missing Python dependency.

Files under 100 MB are uploaded directly to `/api`; larger files use the Nginx upload module at `/upload`.

## API Endpoint (`/api`)

POST with HTTP Basic Auth or session authentication. Actions:

| Action | Description |
|--------|-------------|
| `version` | Get server version |
| `push` | Upload a package file |
| `push_doc` | Upload documentation archive (.zip/.tgz), extracted per branch |
| `delete` | Delete a revision item |

GET returns the client script (`api.py`).

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
├── server/
│   ├── config/
│   │   ├── nginx.conf                  # Main Nginx config
│   │   └── http.d/Django_server.conf   # Server block (static/media/upload/proxy)
│   ├── data/
│   │   ├── static/                     # CSS, JS, images, client script
│   │   └── templates/                  # HTML templates
│   └── scripts/                        # Django project root
│       ├── manage.py
│       ├── scripts/                    # Django settings module
│       ├── delivery/                   # Main app: packages, news, branches, API
│       └── connector/                  # User auth & profiles
```

## Roadmap

- [ ] 0.5.0
    - [ ] OAuth authentication support
    - [ ] Email notifications
        - [ ] Tunable notification preferences
        - [ ] New release notifications
        - [ ] Comment notifications
- [x] 0.4.0 — 2026-03-04
    - [x] Modernize the UI
    - [x] Modernize the backend
- [x] 0.3.1 — 2025-02-05
    - [x] Hotfix: correct API problem with file suffixes
- [x] 0.3.0 — 2025-02-05
    - [x] Engine API documentation pages
    - [x] Branch display management (stable vs dev, visibility toggle)
- [x] 0.2.0 — 2025-02-03
    - [x] Revision reorganization with branch filtering
- [x] 0.1.0 — 2024-05-18
    - [x] User management (login, registration, permissions, profile, password reset)
    - [x] Revision management (browsing, push script, automated upload)
    - [x] Admin sections (delete revisions/items)
