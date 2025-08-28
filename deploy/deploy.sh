#!/usr/bin/env bash
set -euo pipefail

APP_DIR=${APP_DIR:-/opt/cloudrtmp}
REPO_URL=${REPO_URL:-}

if [[ -z "$REPO_URL" ]] && [[ ! -d .git ]]; then
  echo "Run from a git repo or set REPO_URL to clone." >&2
  exit 1
fi

sudo mkdir -p "$APP_DIR"
sudo chown -R "$USER":"$USER" "$APP_DIR"

if [[ -n "$REPO_URL" ]]; then
  if [[ -d "$APP_DIR/.git" ]]; then
    git -C "$APP_DIR" fetch --all --prune
    git -C "$APP_DIR" checkout main
    git -C "$APP_DIR" pull --ff-only
  else
    git clone "$REPO_URL" "$APP_DIR"
  fi
else
  rsync -a --delete --exclude .git ./ "$APP_DIR"/
fi

cd "$APP_DIR"

docker compose pull || true
docker compose build --no-cache
docker compose up -d

echo "Running alembic migrations..."
docker compose exec -T backend bash -lc "alembic upgrade head" || true

echo "CloudRTMP deployed. Backend on port 8000, Frontend on 5173."


