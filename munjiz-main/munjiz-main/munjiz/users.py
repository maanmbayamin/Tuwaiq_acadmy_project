"""Who can sign in, and what each role may see.

Two sides:
- Participant (pavilion team): signs in with the pavilion code; sees only its own pavilion's tickets.
- Expo Admin: desk staff (their desk only), supervisor (SLA alerts, reassign, override), organiser
  (dashboard, rules, full event log).

These are DEMO accounts with demo codes. A pilot would use the Expo's single sign-on or the digital ID
from challenge 5.2 instead.
"""
import hashlib
import hmac
import re
import secrets

from . import expo
from .db import connect, row

PARTICIPANT, DESK_STAFF, SUPERVISOR, ORGANISER = "participant", "desk_staff", "supervisor", "organiser"
ADMIN_ROLES = (DESK_STAFF, SUPERVISOR, ORGANISER)

ROLE_LABEL = {
    PARTICIPANT: "Participant · pavilion team",
    DESK_STAFF: "Expo Admin · desk staff",
    SUPERVISOR: "Expo Admin · supervisor",
    ORGANISER: "Expo Admin · organiser",
}

# Pages each role can open (names match app.py).
PAGES = {
    PARTICIPANT: ["participant"],
    DESK_STAFF: ["staff"],
    SUPERVISOR: ["supervisor", "staff", "tracker"],
    ORGANISER: ["dashboard", "tracker", "rules"],
}

PAVILION_CODES = {
    "France Pavilion": "FRA-2030",
    "Bahrain Pavilion": "BHR-2030",
    "Oman Pavilion": "OMN-2030",
    "Switzerland Pavilion": "CHE-2030",
    "International Organisation Pavilion (example)": "IO-2030",
    "Corporate Pavilion (example)": "CORP-2030",
}
STAFF_PIN = "2030"


def participant_id(pavilion: str) -> str:
    """Non-secret account id (it appears in the sign-in link): "France Pavilion" -> p-france."""
    name = pavilion.replace(" (example)", "").replace(" Pavilion", "")
    return "p-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# (id, name, role, desk, pavilion, code). The pavilion code is only stored hashed, as the participant's credential.
DEMO_USERS = [
    *[(participant_id(name), name.replace(" (example)", ""), PARTICIPANT, None, name, code)
      for name, code in PAVILION_CODES.items()],
    ("logistics.officer", "Logistics officer", DESK_STAFF, "logistics", None, STAFF_PIN),
    ("security.officer", "Accreditation officer", DESK_STAFF, "security", None, STAFF_PIN),
    ("facilities.officer", "Utilities officer", DESK_STAFF, "facilities", None, STAFF_PIN),
    ("logistics.officer2", "Logistics officer (2)", DESK_STAFF, "logistics", None, STAFF_PIN),
    ("security.officer2", "Accreditation officer (2)", DESK_STAFF, "security", None, STAFF_PIN),
    ("facilities.officer2", "Utilities officer (2)", DESK_STAFF, "facilities", None, STAFF_PIN),
    ("ops.supervisor", "Participant services supervisor", SUPERVISOR, None, None, STAFF_PIN),
    ("expo.organiser", "Expo organiser", ORGANISER, None, None, STAFF_PIN),
]
assert set(PAVILION_CODES) == set(expo.PARTICIPANTS)


def _hash(code: str) -> str:
    return hashlib.sha256(f"munjiz:{code.strip().upper()}".encode()).hexdigest()


_seeded: set = set()


def seed():
    """Create the demo accounts once per database (codes are reset to the demo values)."""
    from . import config
    if str(config.DB_PATH) in _seeded and config.DB_PATH.exists():
        return
    ids = [u[0] for u in DEMO_USERS]
    with connect() as conn:
        # Participant accounts used to be keyed by their pavilion code: drop those rows.
        conn.execute(f"DELETE FROM users WHERE role=? AND id NOT IN ({','.join('?' * len(ids))})", (PARTICIPANT, *ids))
        conn.executemany(
            "INSERT OR REPLACE INTO users (id, name, role, desk, pavilion, code_hash) VALUES (?,?,?,?,?,?)",
            [(i, n, r, d, p, _hash(c)) for i, n, r, d, p, c in DEMO_USERS])
    _seeded.add(str(config.DB_PATH))


def all_users() -> list[dict]:
    seed()
    with connect() as conn:
        rows = [row(r) for r in conn.execute("SELECT id, name, role, desk, pavilion FROM users ORDER BY rowid")]
    return rows


def sign_in(user_id: str, code: str) -> dict | None:
    seed()
    with connect() as conn:
        r = conn.execute("SELECT id, name, role, desk, pavilion, code_hash FROM users WHERE id=?",
                         (user_id.strip().lower(),)).fetchone()
    if r is None or r["code_hash"] != _hash(code):
        return None
    user = row(r)
    user.pop("code_hash")
    return user


def sign_in_with_pavilion_code(code: str) -> dict | None:
    """Participants only type their pavilion code; it is matched against the stored hash."""
    seed()
    with connect() as conn:
        r = conn.execute("SELECT id, name, role, desk, pavilion FROM users WHERE role=? AND code_hash=?",
                         (PARTICIPANT, _hash(code))).fetchone()
    return row(r) if r else None


def officers(desk: str) -> list[str]:
    return [u["id"] for u in all_users() if u["role"] == DESK_STAFF and u["desk"] == desk]


def can_open(user: dict | None, page: str) -> bool:
    return bool(user) and page in PAGES[user["role"]]


def is_admin(user: dict | None) -> bool:
    return bool(user) and user["role"] in ADMIN_ROLES


def visible_desks(user: dict) -> list[str]:
    from .config import DESKS
    return [user["desk"]] if user["role"] == DESK_STAFF else list(DESKS) if is_admin(user) else []


# A browser refresh starts a new Streamlit session. The sign-in survives it through a signed token in the URL:
# the account id (never a code or PIN) plus an HMAC. Without a real MUNJIZ_API_TOKEN the key is random per server
# process, so sign-ins then just don't survive a server restart.
_PROCESS_SECRET = secrets.token_hex(32)


def _secret() -> bytes:
    from . import config
    token = config.API_TOKEN.strip()
    return (token if token and token != "change-me" else _PROCESS_SECRET).encode()


def _sign(uid: str) -> str:
    return hmac.new(_secret(), uid.encode(), "sha256").hexdigest()[:20]


def session_token(user: dict) -> str:
    return f"{user['id']}.{_sign(user['id'])}"


def from_token(token: str | None) -> dict | None:
    if not token or "." not in token:
        return None
    uid, sig = token.rsplit(".", 1)
    try:
        if not hmac.compare_digest(sig.encode(), _sign(uid).encode()):
            return None
    except (TypeError, ValueError, UnicodeError):
        return None
    seed()
    with connect() as conn:
        r = conn.execute("SELECT id, name, role, desk, pavilion FROM users WHERE id=?", (uid,)).fetchone()
    return row(r) if r else None
