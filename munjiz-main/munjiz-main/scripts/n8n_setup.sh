#!/usr/bin/env bash
# First-time n8n setup: .env with a fresh token, start n8n, import and activate the Munjiz workflows.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
  token=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
  sed -i '' "s/^MUNJIZ_API_TOKEN=.*/MUNJIZ_API_TOKEN=${token}/" .env 2>/dev/null || sed -i "s/^MUNJIZ_API_TOKEN=.*/MUNJIZ_API_TOKEN=${token}/" .env
  echo "Created .env with a new API token"
fi

python3 n8n/make_workflows.py
scripts/n8n_container.sh

wait_for_n8n() {
  for _ in $(seq 1 60); do
    curl -fs http://localhost:5678/healthz >/dev/null 2>&1 && return 0
    sleep 2
  done
  echo "n8n did not start; check: docker logs munjiz-n8n" >&2
  exit 1
}
wait_for_n8n

docker exec munjiz-n8n n8n import:workflow --separate --input=/workflows
docker exec munjiz-n8n n8n update:workflow --all --active=true
docker restart munjiz-n8n >/dev/null   # activation takes effect on restart
wait_for_n8n

echo
echo "n8n is ready at http://localhost:5678 (create the owner account on first visit)."
echo "Workflows: Route ticket to desks · SLA watchdog · Desk decision intake"
