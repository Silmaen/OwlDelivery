# Changelog

What has shipped, newest first. What is planned lives in [ROADMAP.md](ROADMAP.md).

## 0.5.0 — in development

- Gunicorn and Nginx timeouts raised and upload concurrency fixed, so large packages no longer fail mid-upload.
- `deploy.sh` deploys on a server in one command: fast-forward, database snapshot, base image refresh, build, health check.
- `/media` only serves `packages/`, `documentation/` and `markdownx/`, so the database and logs are no longer downloadable.
- Base images pinned on a version (Python 3.14 Alpine), refreshed at every deployment.
- Changelog and roadmap moved out of the README into `CHANGELOG.md` and `ROADMAP.md`.

## 0.4.0 — 2026-03-04

- New user interface: design tokens, BEM components, responsive layout and mobile navigation.
- Backend modernized: Django 6, Docker Compose, container user ownership of the data volume.

## 0.3.1 — 2025-02-05

- API fix for the suffixes of package files.

## 0.3.0 — 2025-02-05

- Engine API documentation pages, uploaded per branch through `push_doc`.
- Branch display management: stable or development, visibility toggle.

## 0.2.0 — 2025-02-03

- Revisions reorganized by branch, with branch filtering.

## 0.1.0 — 2024-05-18

- User management: login, registration, permissions, profile, password reset.
- Revision management: browsing, push script, automated upload.
- Admin sections to delete revisions and revision items.
