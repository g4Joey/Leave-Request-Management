#!/usr/bin/env bash

# Automated deploy script for DigitalOcean droplet
# - Pull latest code
# - Install backend deps and run migrations
# - Build frontend
# - Collect static
# - Restart services (systemd or docker compose)

set -Eeuo pipefail

have_cmd() { command -v "$1" >/dev/null 2>&1; }

# Config (can be overridden by environment)
PROJECT_DIR="${PROJECT_DIR:-/opt/leave-management}"
GUNICORN_SERVICE="${GUNICORN_SERVICE:-gunicorn}"
NGINX_SERVICE="${NGINX_SERVICE:-nginx}"

echo "[deploy] Starting deployment at $(date -Is)"

# Move to project directory when it exists; otherwise use current directory
if [ -d "$PROJECT_DIR/.git" ]; then
  cd "$PROJECT_DIR"
else
  echo "[deploy] WARN: PROJECT_DIR ($PROJECT_DIR) not found; using current directory $(pwd)"
fi

echo "[deploy] Git pull..."
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if git pull --ff-only origin main; then
    echo "[deploy] Pulled latest from origin/main"
  else
    echo "[deploy] git pull failed; attempting fetch/reset"
    git fetch --all --prune
    git reset --hard origin/main
  fi
else
  echo "[deploy] ERROR: Not a git repository here: $(pwd)" >&2
  exit 1
fi

echo "[deploy] Python venv & dependencies..."
if ! [ -d .venv ]; then
  if have_cmd python3; then
    python3 -m venv .venv
  else
    echo "[deploy] ERROR: python3 not found" >&2
    exit 1
  fi
fi

source .venv/bin/activate
python -m pip install -U pip wheel
python -m pip install -r requirements.txt

echo "[deploy] Django migrations..."
python manage.py migrate --noinput

echo "[deploy] Ensure notifications migrations & seeds..."
python manage.py ensure_notifications_ready || true

echo "[deploy] Frontend build..."
if [ -d frontend ]; then
  if have_cmd npm; then
    pushd frontend >/dev/null
    npm ci
    npm run build
    popd >/dev/null
  else
    echo "[deploy] WARN: npm not found; skipping frontend build. Make sure assets are already built."
  fi
else
  echo "[deploy] No frontend directory; skipping build."
fi

echo "[deploy] Collect static files..."
python manage.py collectstatic --noinput

echo "[deploy] Restarting services..."
# Prefer docker compose when docker-compose file exists
if [ -f docker-compose.yml ] || [ -f docker-compose.prod.yml ]; then
  if have_cmd docker; then
    if have_cmd docker-compose; then
      docker-compose up -d --build
    else
      docker compose up -d --build
    fi
  else
    echo "[deploy] ERROR: docker not found but docker-compose.yml exists" >&2
    exit 1
  fi
else
  # Fallback to systemd restarts
  if have_cmd systemctl; then
    sudo systemctl restart "$GUNICORN_SERVICE" || true
    sudo systemctl restart "$NGINX_SERVICE" || true
  else
    echo "[deploy] WARN: systemctl not found; please restart your app server manually"
  fi
fi

echo "[deploy] Completed at $(date -Is)"
