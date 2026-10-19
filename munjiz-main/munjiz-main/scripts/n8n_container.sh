#!/usr/bin/env bash
# Start (or reuse) the munjiz-n8n container with plain `docker run`. Same settings as docker-compose.yml.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; [ -f .env ] && . ./.env; set +a

if docker ps -a --format '{{.Names}}' | grep -qx munjiz-n8n; then
  docker start munjiz-n8n >/dev/null
else
  docker run -d --name munjiz-n8n --restart unless-stopped -p 5678:5678 \
    -e GENERIC_TIMEZONE=Asia/Riyadh -e TZ=Asia/Riyadh \
    -e N8N_SECURE_COOKIE=false -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_PERSONALIZATION_ENABLED=false \
    -e N8N_BLOCK_ENV_ACCESS_IN_NODE=false -e N8N_RUNNERS_ENABLED=true -e N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true \
    -e MUNJIZ_API_URL="${MUNJIZ_PUBLIC_API_URL:-http://host.docker.internal:8000}" \
    -e MUNJIZ_API_TOKEN="${MUNJIZ_API_TOKEN:-}" \
    --add-host host.docker.internal:host-gateway \
    -v munjiz_n8n_data:/home/node/.n8n \
    -v "$PWD/n8n/workflows:/workflows:ro" \
    docker.n8n.io/n8nio/n8n:1.88.0 >/dev/null
fi
