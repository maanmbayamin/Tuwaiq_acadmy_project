import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path):
    """Minimal .env reader: KEY=value lines; real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env")

RULES_DIR = ROOT / "rules"
DB_PATH = Path(os.environ.get("MUNJIZ_DB", ROOT / "data" / "munjiz.db"))
CACHE_DIR = ROOT / "data" / "llm_cache"

TZ = ZoneInfo("Asia/Riyadh")
DESKS = ["logistics", "security", "facilities"]

# "local" = offline parser (free, deterministic). "claude" = Claude tool use.
BACKEND = os.environ.get("MUNJIZ_BACKEND", "local")
CLAUDE_MODEL = os.environ.get("MUNJIZ_MODEL", "claude-sonnet-5-5")

# n8n integration. Empty webhook URL = integration off; the app works the same without it.
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "")
# How n8n (inside Docker) reaches the Munjiz API, and the token it must send back.
PUBLIC_API_URL = os.environ.get("MUNJIZ_PUBLIC_API_URL", "http://host.docker.internal:8000")
API_TOKEN = os.environ.get("MUNJIZ_API_TOKEN", "")

# The demo runs on a simulated Expo date: today's real time of day, moved to EXPO_DATE (Expo day 48 by default),
# so "tomorrow" means a day of the Expo. Every process gets the same clock. MUNJIZ_CLOCK=real uses the real date.
CLOCK = os.environ.get("MUNJIZ_CLOCK", "expo")
EXPO_DATE = date.fromisoformat(os.environ.get("MUNJIZ_EXPO_DATE", "2030-11-17"))
_OFFSET = EXPO_DATE - datetime.now(TZ).date()


def now() -> datetime:
    real = datetime.now(TZ)
    return real + _OFFSET if CLOCK == "expo" else real
