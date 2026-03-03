---
globs: "*"
---

# General Project Rules

## Language

This project is maintained by a French-speaking developer. Respond in the language the user writes in.

## Project Overview

OwlDelivery is a Django web application for hosting Owl Game Engine packages. It runs in Docker with Nginx (reverse proxy + large file upload module) and Gunicorn.

## Workflow

```bash
cp .env.sample .env     # first time only
docker compose build    # build image
docker compose up       # run (Ctrl+C to stop)
```

No `pip`, `python manage.py`, or direct Django commands on the host — everything runs inside the container.

## Key Paths (inside container)

- Django project: `/app/server/scripts/`
- Database: `/app/data/delivery.db`
- Packages: `/app/data/packages/{branch}/{hash}/{filename}`
- Static collected: `/app/staticfiles/`
- Logs: `/app/data/log/`
- Nginx config: `/app/server/config/nginx.conf`

## Git

- `server/VERSION` is generated at build time — never commit it manually
- `docker_data/` is gitignored (runtime data volume)
- `.env` is gitignored (contains secrets)
