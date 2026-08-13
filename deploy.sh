#!/usr/bin/env bash
#
# All-in-one deployment for the OwlDelivery server: git, build, start, health check.
#
# Migrations, collectstatic and the admin account are handled by entrypoint.py when the
# `web` container starts, so this script does not repeat them.
#
#   ./deploy.sh                 full deployment (pull + build + up + wait)
#   ./deploy.sh --no-pull       fetch nothing: neither the git update nor the images
#   ./deploy.sh --no-backup     skip the database snapshot
#   ./deploy.sh --dry-run       print what would run, execute nothing
#   ./deploy.sh check           only look for a pending update, change nothing
#   ./deploy.sh status          service status
#   ./deploy.sh logs [service]  follow the logs
#   ./deploy.sh stop            stop everything
#   ./deploy.sh restart         restart without rebuilding
#   ./deploy.sh backup          snapshot the database, deploy nothing
#   ./deploy.sh superuser       create an admin account
#   ./deploy.sh shell           Django shell inside the web container
#   ./deploy.sh help            this help
#
# `check` (alias `--check`) exits with a status meant to be scripted:
#   0   already up to date
#   10  an update is pending
#   1   cannot tell (not a git repository, no upstream, fetch failed)
#
# Called with no argument by the fleet console's deploy button, through the wake agent
# of home-server-stacks: it runs this file as the owner of the checkout, with stdin on
# /dev/null and no argument at all. Hence a bare `./deploy.sh` has to be the complete,
# non-interactive deployment, and nothing here may ask a question.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# The Django project root inside the container: manage.py needs to run from there for
# `scripts.settings` to be importable.
MANAGE=(-w /app/server/scripts web python3 manage.py)
# The only service, and it carries a healthcheck, so it can be waited on.
WATCHED_SERVICES=(web)
HEALTH_TIMEOUT=180
# Outside the data volume on purpose: nginx serves the whole of /app/data at /media, so
# a snapshot dropped in there would be downloadable by anyone.
BACKUP_DIR="$ROOT/docker_data/backup"
BACKUP_KEEP=5

PULL=1
BACKUP=1
DRY_RUN=0

# --- Output ------------------------------------------------------------------

if [ -t 1 ]; then
    C_STEP=$'\033[1;34m'; C_OK=$'\033[0;32m'; C_WARN=$'\033[0;33m'
    C_ERR=$'\033[0;31m'; C_END=$'\033[0m'
else
    C_STEP=""; C_OK=""; C_WARN=""; C_ERR=""; C_END=""
fi

step() { printf '\n%s==> %s%s\n' "$C_STEP" "$1" "$C_END"; }
ok()   { printf '%s  ✓ %s%s\n' "$C_OK" "$1" "$C_END"; }
warn() { printf '%s  ! %s%s\n' "$C_WARN" "$1" "$C_END"; }
fail() { printf '%s  ✗ %s%s\n' "$C_ERR" "$1" "$C_END" >&2; exit 1; }

# Run a command, or just print it in --dry-run mode.
run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '  [dry-run] %s\n' "$*"
        return 0
    fi
    "$@"
}

# The help text is the file header: one place to keep up to date.
usage() {
    awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "${BASH_SOURCE[0]}"
}

# --- Preflight checks --------------------------------------------------------

check_tools() {
    command -v docker >/dev/null 2>&1 || fail "docker not found."
    docker compose version >/dev/null 2>&1 \
        || fail "the 'docker compose' plugin is missing (docker-compose v1 is not supported)."
    docker info >/dev/null 2>&1 \
        || fail "the docker daemon is not responding: is it running, and is your account in the docker group?"
    ok "docker and docker compose available"
}

# Read a variable from .env, falling back to the given default.
#
# The trailing CR is stripped: a .env saved from Windows turns every value into
# `value<CR>`, and that is not a theoretical worry -- it silently made this script
# create a *second* data directory whose name ended in a carriage return, and
# report "no database yet" about a database sitting right there. docker compose
# strips it on its side, which is exactly what made the mismatch confusing: the
# container was running fine on the file this script could not read.
env_value() {
    local key="$1" default="${2:-}" line
    line="$(grep -E "^${key}=" .env 2>/dev/null | tail -1 || true)"
    if [ -z "$line" ]; then
        printf '%s' "$default"
    else
        line="${line#*=}"
        printf '%s' "${line%$'\r'}"
    fi
}

check_env() {
    if [ ! -f .env ]; then
        warn ".env missing, copying .env.sample"
        cp .env.sample .env
        fail "edit .env (at least DOMAIN_NAME, ADMIN_PASSWD, PORT) then run again."
    fi
    # docker compose does strip the trailing CR, both for `env_file` and for interpolation
    # (checked: DOMAIN_NAME arrives clean in the container, and the volume path resolves),
    # so this is a warning and not a failure. It is still worth saying: every *other*
    # reader has to know to strip it -- this script does, in env_value -- and the project
    # requires LF everywhere.
    if grep -q $'\r' .env 2>/dev/null; then
        warn ".env has CRLF line endings: convert it to LF (dos2unix .env)"
    fi
    # DOMAIN_NAME is what CSRF_TRUSTED_ORIGINS is built from: left at the sample value
    # the site serves fine and every POST is rejected, which is a confusing way to
    # discover a deployment problem.
    local domain admin
    domain="$(env_value DOMAIN_NAME)"
    case "$domain" in
        ""|example.com) warn "DOMAIN_NAME is '$domain': every POST will be refused by CSRF" ;;
    esac
    admin="$(env_value ADMIN_PASSWD)"
    [ "$admin" = "admin" ] && warn "ADMIN_PASSWD is still the sample password"
    ok ".env present"
}

# The data directory must exist *before* the first `up`: otherwise Docker creates it as
# root. entrypoint.py does chown it to PUID/PGID afterwards, but only what is inside it
# -- the mount point itself stays root-owned and the owner can no longer clean it.
prepare_directories() {
    local data
    data="$(env_value PATH_DATA ./docker_data/data)"
    if [ ! -d "$data" ]; then
        run mkdir -p "$data"
        ok "data directory created: $data"
    fi
}

# --- Steps -------------------------------------------------------------------

# entrypoint.py runs makemigrations *and* migrate on every start, so a deployment can
# alter the schema of a database this script has not been asked to touch. A copy costs a
# second and an SQLite file, and is the difference between a bad migration being an
# annoyance and being the end of the package history.
#
# SQLite's online backup API rather than `cp`: it is safe on a database with a live
# writer, which is exactly the situation here since this runs before the container is
# stopped -- a plain copy of a busy SQLite file can land mid-transaction. The sqlite3
# CLI is not installed on these hosts, python3 always is (ansible needs it), and `cp`
# remains as a last resort: a best-effort snapshot beats none, and it is reported.
backup_database() {
    local data db stamp target
    data="$(env_value PATH_DATA ./docker_data/data)"
    db="$data/delivery.db"
    step "Backing up the database"
    if [ ! -f "$db" ]; then
        warn "no database yet at $db, nothing to back up"
        return 0
    fi
    stamp="$(date +%Y%m%d-%H%M%S)"
    target="$BACKUP_DIR/delivery-$stamp.db"
    run mkdir -p "$BACKUP_DIR"
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '  [dry-run] snapshot %s -> %s\n' "$db" "$target"
        return 0
    fi
    if command -v sqlite3 >/dev/null 2>&1; then
        sqlite3 "$db" ".backup '$target'" || fail "the snapshot of $db failed."
    elif command -v python3 >/dev/null 2>&1; then
        python3 - "$db" "$target" <<'PY' || fail "the snapshot of $db failed."
import sqlite3, sys

source, target = sys.argv[1], sys.argv[2]
# Read-only on the source: this must not be the writer that creates a -wal file next
# to a database the container owns.
with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as src, sqlite3.connect(target) as dst:
    src.backup(dst)
PY
    else
        warn "neither sqlite3 nor python3 on the host, falling back to cp"
        cp "$db" "$target" || fail "the copy of $db failed."
    fi
    ok "snapshot: $target ($(du -h "$target" | cut -f1))"
    # Keep the last few and no more: this directory is not a backup policy, it is an
    # undo button for a deployment. The real backups are hestia's job.
    local old
    old="$(ls -1t "$BACKUP_DIR"/delivery-*.db 2>/dev/null | tail -n +$((BACKUP_KEEP + 1)) || true)"
    if [ -n "$old" ]; then
        printf '%s\n' "$old" | xargs -r rm -f
        ok "$(printf '%s\n' "$old" | wc -l) older snapshot(s) removed"
    fi
}

update_repository() {
    step "Updating the repository"
    if [ ! -d .git ]; then
        warn "not a git repository, skipping the update"
        return 0
    fi
    if [ -n "$(git status --porcelain)" ]; then
        git status --short
        fail "the repository has local changes: commit them, stash them, or use --no-pull."
    fi
    local before
    before="$(git rev-parse HEAD)"
    run git pull --ff-only
    if [ "$DRY_RUN" -eq 0 ]; then
        local after
        after="$(git rev-parse HEAD)"
        if [ "$before" = "$after" ]; then
            ok "already up to date ($(git rev-parse --short HEAD))"
        else
            ok "updated: $(git rev-parse --short "$before") -> $(git rev-parse --short "$after")"
            git --no-pager log --oneline "$before..$after"
        fi
    fi
}

# Report whether the remote is ahead, and touch nothing else. `git fetch` only writes
# remote-tracking refs, never the working tree, so this is safe to run on a schedule.
check_update() {
    step "Checking for a pending update"
    [ -d .git ] || fail "not a git repository, cannot check for updates."

    local branch upstream
    branch="$(git rev-parse --abbrev-ref HEAD)"
    [ "$branch" != "HEAD" ] || fail "detached HEAD: there is no branch to compare."
    # for-each-ref rather than `rev-parse --symbolic-full-name '@{upstream}'`: on a branch
    # with no upstream the latter echoes the literal `@{upstream}` back and exits 0, so the
    # guard below passed and the comparison three lines further down died on "ambiguous
    # argument". An empty string is an answer that can be tested.
    upstream="$(git for-each-ref --format='%(upstream:short)' "refs/heads/$branch")"
    [ -n "$upstream" ] || fail "branch '$branch' tracks no upstream: nothing to compare against."

    if [ "$DRY_RUN" -eq 1 ]; then
        printf '  [dry-run] git fetch --quiet\n'
        warn "comparing against the remote refs already on disk"
    else
        git fetch --quiet || fail "git fetch failed: is the remote reachable?"
    fi

    local counts behind ahead
    counts="$(git rev-list --left-right --count "${upstream}...HEAD" 2>/dev/null)" \
        || fail "'$upstream' is not on disk: this branch was never pushed, or never fetched."
    read -r behind ahead <<< "$counts"
    ok "branch '$branch' tracking '$upstream'"

    # A dirty tree does not block this check, but it will block the deployment.
    if [ -n "$(git status --porcelain)" ]; then
        warn "local changes present: a deployment will need --no-pull"
    fi

    if [ "$ahead" -gt 0 ] && [ "$behind" -eq 0 ]; then
        ok "up to date ($ahead local commit(s) not pushed)"
        return 0
    fi

    if [ "$behind" -eq 0 ]; then
        ok "up to date ($(git rev-parse --short HEAD))"
        return 0
    fi

    if [ "$ahead" -gt 0 ]; then
        warn "branches have diverged: $behind incoming, $ahead local commit(s)"
    else
        warn "$behind commit(s) pending"
    fi
    git --no-pager log --oneline "HEAD..${upstream}"
    printf '\n     deploy with: ./deploy.sh\n'
    exit 10
}

# Refresh the images the build starts from. Nothing here comes from a registry at run
# time -- the only service is built locally -- so `docker compose pull` has nothing to
# do and the whole job is the Dockerfile's bases: a pinned `python:3.14-alpine` stays on
# whatever was pulled the first time, and the patch releases, which is where the
# security fixes are, would never land. This is also the counterpart of the
# `wud.watch: 'false'` label in docker-compose.yml: wud cannot watch an image that
# exists in no registry, so the refresh has to happen here.
#
# The tags are read from the Dockerfile rather than repeated here, and stage names
# (`FROM x AS name`, then `FROM name`) are skipped: they are not pullable references.
#
# A registry we cannot reach is a warning, not a failure: the images already on disk are
# enough to deploy, and aborting would leave the update half done.
pull_images() {
    step "Refreshing the base images"
    local stale=0 stages base
    stages="$(awk 'toupper($1) == "FROM" && toupper($3) == "AS" { print $4 }' Dockerfile)"
    while read -r base; do
        [ -n "$base" ] || continue
        [ "$base" = "scratch" ] && continue
        printf '%s\n' "$stages" | grep -qxF "$base" && continue
        run docker pull --quiet "$base" || stale=1
    done < <(awk 'toupper($1) == "FROM" { print $2 }' Dockerfile | sort -u)
    if [ "$stale" -eq 1 ]; then
        warn "some images could not be refreshed, keeping the ones already on disk"
    else
        ok "base images up to date"
    fi
}

build_image() {
    step "Building the image"
    # server/VERSION is generated from .git by the first stage, so the build context
    # includes the repository: a shallow or exported tree would build a version-less
    # image rather than fail, which is worth catching here.
    [ -d .git ] || warn "no .git in the context: server/VERSION will have no commit hash"
    run docker compose build
    ok "image built"
}

start_services() {
    step "Starting the services"
    run docker compose up -d
    ok "services started"
}

# Wait for a service to become healthy, or fail showing its last log lines.
wait_for_service() {
    local service="$1" elapsed=0 cid health status
    cid="$(docker compose ps -q "$service" 2>/dev/null || true)"
    [ -n "$cid" ] || fail "service $service did not start."

    while [ "$elapsed" -lt "$HEALTH_TIMEOUT" ]; do
        status="$(docker inspect -f '{{.State.Status}}' "$cid")"
        [ "$status" = "running" ] || break
        health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$cid")"
        case "$health" in
            healthy|no-healthcheck) ok "$service: $health"; return 0 ;;
            unhealthy) break ;;
        esac
        sleep 3
        elapsed=$((elapsed + 3))
        printf '\r  ... %s: %s (%ss)' "$service" "$health" "$elapsed"
    done
    printf '\n'
    docker compose logs --tail 40 "$service" || true
    fail "$service did not become operational within ${HEALTH_TIMEOUT}s."
}

check_health() {
    step "Checking health"
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '  [dry-run] would wait for: %s\n' "${WATCHED_SERVICES[*]}"
        return 0
    fi
    local service
    for service in "${WATCHED_SERVICES[@]}"; do
        wait_for_service "$service"
    done
}

summary() {
    step "Service status"
    docker compose ps
    local port version
    # Asked of the running container rather than of .env: an operator who exports PORT
    # for one run must not be told the port the file says.
    port="$(docker compose port web 80 2>/dev/null | head -1 | sed 's/.*://')"
    [ -n "$port" ] || port="$(env_value PORT 8080)"
    version="$(docker compose exec -T web cat /app/server/VERSION 2>/dev/null | tr '\n' ' ' || true)"
    printf '\n'
    ok "site available at http://localhost:${port}/"
    [ -n "$version" ] && printf '     version: %s\n' "$version"
    printf '     logs:    ./deploy.sh logs\n'
}

deploy() {
    step "Deploying OwlDelivery"
    [ "$DRY_RUN" -eq 1 ] && warn "--dry-run mode: no command is executed"
    check_tools
    check_env
    prepare_directories
    [ "$PULL" -eq 1 ] && update_repository
    [ "$BACKUP" -eq 1 ] && backup_database
    [ "$PULL" -eq 1 ] && pull_images
    build_image
    start_services
    check_health
    [ "$DRY_RUN" -eq 0 ] && summary
    return 0
}

# --- Entry point -------------------------------------------------------------

COMMAND="deploy"
ARGUMENT=""

while [ $# -gt 0 ]; do
    case "$1" in
        --no-pull)   PULL=0 ;;
        --no-backup) BACKUP=0 ;;
        --dry-run)   DRY_RUN=1 ;;
        -h|--help|help) usage; exit 0 ;;
        --check)     COMMAND="check" ;;
        deploy|check|status|logs|stop|restart|backup|superuser|shell)
            COMMAND="$1"
            if [ $# -gt 1 ] && [[ "$2" != -* ]]; then
                ARGUMENT="$2"
                shift
            fi
            ;;
        *) fail "unknown argument: $1 (see ./deploy.sh help)" ;;
    esac
    shift
done

case "$COMMAND" in
    deploy)    deploy ;;
    check)     check_update ;;
    status)    check_tools; docker compose ps ;;
    logs)      docker compose logs -f ${ARGUMENT:+"$ARGUMENT"} ;;
    stop)      step "Stopping"; docker compose down; ok "services stopped" ;;
    restart)   step "Restarting"; docker compose restart; check_health; summary ;;
    backup)    check_tools; backup_database ;;
    superuser) docker compose exec "${MANAGE[@]}" createsuperuser ;;
    shell)     docker compose exec "${MANAGE[@]}" shell ;;
esac
