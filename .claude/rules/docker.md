---
paths:
  - "Dockerfile"
  - "docker-compose.yml"
  - "entrypoint.py"
  - ".env.sample"
  - "requirements.txt"
---

# Docker Conventions

## Image

- Base: `python:3.13-alpine`
- Multi-stage build: first stage (`alpine/git`) extracts git hash, second stage builds the app
- `server/VERSION` is generated at build time with version number + git short hash

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
