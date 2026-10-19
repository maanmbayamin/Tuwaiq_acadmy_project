#!/usr/bin/env bash
# Start the Munjiz API (for n8n callbacks) and the Streamlit app. Ctrl+C stops both.
set -euo pipefail
cd "$(dirname "$0")/.."

scripts/n8n_container.sh 2>/dev/null || echo "n8n not started (Docker off?); Munjiz runs without it."
# 0.0.0.0 so n8n inside Docker can reach the API; write endpoints need the token from .env.
python3 -m uvicorn munjiz.api:app --host 0.0.0.0 --port 8000 --log-level warning &
api=$!
trap 'kill $api 2>/dev/null' EXIT
python3 -m streamlit run app.py --server.port 8501
