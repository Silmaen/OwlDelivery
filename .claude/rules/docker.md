---
paths:
  - "Dockerfile"
  - "docker-compose.yml"
  - "entrypoint.py"
  - ".env.sample"
  - "requirements.txt"
  - "deploy.sh"
---

# Docker Conventions

## Image

- Base: `python:3.14-alpine`
- Multi-stage build: first stage (`alpine/git:v2.54.0`) extracts git hash, second stage builds the app
- Both `FROM` tags are **pinned on a version, never floating** (`latest`, bare `3`): `deploy.sh`
  pulls them at every deployment so patch releases land, and a bump is a commit
- `server/VERSION` is generated at build time with version number + git short hash

## docker-compose.yml

- `wud.watch: 'false'` on `web`: the image is built here and exists in no registry, so
  [wud](https://github.com/getwud/wud) would report a 401 on `library/owldelivery-web:latest`.
  What this image really tracks is the Dockerfile's bases, refreshed by `deploy.sh`
- `healthcheck` on `http://127.0.0.1/` (busybox wget): the root page goes through nginx *and*
  gunicorn *and* needs a migrated database, so it covers the whole chain. `deploy.sh` waits on it

## deploy.sh

Single entry point for a deployment on the server (see the file header for the commands).
Constraints it must keep satisfying, because the fleet console of `home-server-stacks`
runs it through its wake agent:

- **executable and committed** — the probe reports no deploy button otherwise
- **no argument, no stdin** — it is invoked as a bare `./deploy.sh`, stdin on `/dev/null`,
  as the owner of the checkout. Nothing may ask a question
- **it must fail on a failed pull** rather than deploy the files already on disk: a button
  labelled "mettre à jour" must not answer "done" when nothing was fetched

## entrypoint.py

Startup sequence:
```
check_env → check_user_exist → check_timezone → correct_permission
→ do_migrations → correct_permission → collect_static
→ check_admin_user → start_server (nginx + gunicorn foreground)
```

**Important patterns:**
- `correct_permission()` runs **twice** (before and after migrations) because `dump_migrations` creates files as root
- `collect_static()` runs as root (`as_root=True`) since `/app/staticfiles/` is container-local
- Gunicorn starts in **foreground** via `os.execvp` (replaces the Python process) — no daemon mode, no sleep loop
- `exec_cmd(cmd, as_root=False)` demotes to PUID/PGID by default; pass `as_root=True` for root commands
- On failure, `fall_back()` drops to a shell for debugging

## Nginx

- Upload module handles `/upload` for large files (up to 8GB)
- Upload temp storage: `/app/data/_upload/{0-9}/` (hashed subdirectories)
- All path references must use `/app/` prefix (e.g., `/app/data/`, `/app/server/`)

## Environment

- `.env.sample` is the template — `.env` is gitignored
- `PUID`/`PGID` control file ownership inside the container
- `PATH_DATA` maps to `/app/data` volume mount

## Line Endings

All files **must** use Unix LF line endings. The shebang in `entrypoint.py` will break with CRLF.
