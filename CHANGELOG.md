# Changelog

What has shipped, newest first. What is planned lives in [ROADMAP.md](ROADMAP.md).

## 0.5.2 — in development

- Editing a screenshot without uploading a new file (caption, alternative text) no longer fails with an error 500.
- A Statistics admin tab shows page views and package downloads per page, per user, per country and referring site of anonymous visitors, and per package.
- Admins, service accounts (new "Service" toggle in the users admin) and robots are left out of the statistics unless asked for.
- Downloads are counted through an nginx mirror, so every link counts without slowing the transfer; no IP address is stored.
- An account allowed to read the statistics counts as an admin, so its own visits leave them.
- The statistics locate visitors by city and network (ISP, organisation), and show where signed-in users connect and came from.
- The statistics count the visitors who viewed several pages and detail the robots and scripts by name.
- The downloads statistics show the version (branch and revision) of each downloaded package.
- Anonymous scripts (curl, wget, python…) from outside get a 403 outside `/api`; an authenticated one or the internal network still passes.
- nginx limits the requests per outside visitor (pages, documentation, downloads) and robots.txt keeps crawlers off the packages and the documentation.

## 0.5.1 — 2026-10-19

- Logout works again: the header posts it, Django 5+ refuses a logout by GET.
- The users admin says why a row is read-only (your own account, a superuser).
- `./deploy.sh password [user]` resets a lost password.
- Long release notes are folded to a few lines, with a button to read them in full (presentation, downloads, branch pages).

## 0.5.0 — 2026-10-18

- Gunicorn and Nginx timeouts raised and upload concurrency fixed, so large packages no longer fail mid-upload.
- `deploy.sh` deploys on a server in one command: fast-forward, database snapshot, base image refresh, build, health check.
- `/media` only serves `packages/`, `documentation/` and `markdownx/`, so the database and logs are no longer downloadable.
- `/api` answers no longer echo the request headers, which carried the HTTP Basic credentials of the caller.
- `/api` refuses `branch`, `hash`, file names and `package.path` that leave their folder: a push could move or delete any file of the data volume.
- `push_doc` checks the archive format before removing the current documentation, and deletes its spooled copy.
- Markdown of news, comments and pages is sanitized with `nh3`: a comment can no longer run a script in a moderator's browser.
- Django's `SECRET_KEY` is no longer committed: it comes from `.env` or is generated once in `PATH_DATA/secret_key`.
- The container logs mask every password, secret, key and token of the environment.
- No more default admin password: with an empty `ADMIN_PASSWD`, the first admin gets a generated one in `PATH_DATA/initial_admin_password`.
- Gunicorn workers run as `PUID`/`PGID` instead of root, without `--reload`.
- Admin news and revision item pages require their permission; anonymous visitors saw every comment.
- A user manager can no longer change their own account or a superuser, nor grant a permission they do not hold.
- Admin actions redirect to fixed pages instead of the `Referer` header.
- Deleting a revision item deletes its archive, which stayed downloadable from its URL.
- `ALLOWED_HOSTS` follows `DOMAIN_NAME` (extra names through `ALLOWED_HOSTS` in `.env`), and cookies are `Secure` behind the TLS proxy.
- API calls in HTTP Basic no longer open a session each.
- The image builds from a git worktree too: the commit hash can be passed with `--build-arg GIT_REV`.
- Packages above 100 MB upload through `/upload` again: the nginx module dropped their fields, `api.py` now also sends them in the query string.
- The custom error pages are used at last: their handlers sat in `settings.py`, where Django never reads them.
- Base images pinned on a version (Python 3.14 Alpine), refreshed at every deployment.
- Changelog and roadmap moved out of the README into `CHANGELOG.md` and `ROADMAP.md`.
- Site name, footer and meta description come from the database (`SiteSettings`), seeded by `manage.py seed_pages` at start.
- News get a draft state (`published`), and the pages say `lang="en"` with a skip link.
- New home page: name and tagline, a Discover link, the latest release with its Download button, the 3 latest news.
- New Presentation tab: screenshots with a lightbox, features, downloads per platform, sample games, roadmap, how it is built.
- Navigation renamed (Presentation, News, Downloads, Docs) and footer links taken from the database.
- The documentation opens under the site header (`/docs/<branch>/`), the address following the doxygen page.
- News: a paginated feed with excerpts, articles with their neighbours and a clearer comment section.
- Downloads: the latest release by version with its buttons, development and older builds as cards, files of a revision by platform.
- The revision admin is paginated (15 per page) with a branch filter, and a deletion returns to the same page.
- OpenGraph tags, canonical URLs, JSON-LD, `robots.txt` and `sitemap.xml` for the public pages.
- Pages admin tab to edit, reorder, publish and preview every text, image and list of both pages.
- A screenshot pushed after the seed reaches the sample games waiting for it, like the hero and social images.
- Users admin gains two toggles: edit the pages, push screenshots and release notes.
- API actions `push_screenshot`, `push_release` and `release_info`, with the matching `api.py` sub-commands, so the engine CI feeds the presentation page.

## 0.4.0 — 2026-03-04

- New user interface: design tokens, BEM components, responsive layout and mobile navigation.
- Backend modernized: Django 6, Docker Compose, container user ownership of the data volume.
- API fix for the suffixes of package files.

## 0.3.0 — 2025-02-05

- Engine API documentation pages, uploaded per branch through `push_doc`.
- Branch display management: stable or development, visibility toggle.

## 0.2.0 — 2025-02-03

- Revisions reorganized by branch, with branch filtering.

## 0.1.0 — 2024-05-19

- User management: login, registration, permissions, profile, password reset.
- Revision management: browsing, push script, automated upload.
- Admin sections to delete revisions and revision items.
