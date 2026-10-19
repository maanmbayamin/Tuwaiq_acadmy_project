"""SQLite store for users, tickets, desk sub-requests and the event log. Mock desk services read and write here."""
import json
import sqlite3
from contextlib import contextmanager

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,              -- sign-in name
    name TEXT NOT NULL,
    role TEXT NOT NULL,               -- participant | desk_staff | supervisor | organiser
    desk TEXT,                        -- desk staff only
    pavilion TEXT,                    -- participants only
    code_hash TEXT NOT NULL           -- pavilion code or staff PIN (demo accounts)
);
CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    pavilion TEXT NOT NULL,
    contact TEXT,
    language TEXT,
    request_text TEXT,
    conversation TEXT,
    status TEXT NOT NULL,             -- in_review | partially_approved | action_needed | completed
    followups INTEGER DEFAULT 0,      -- agent follow-up questions before confirmation
    conflicts_caught INTEGER DEFAULT 0,  -- cross-desk clashes the agent caught before submission
    started_at TEXT,                  -- participant's first message
    created_at TEXT NOT NULL,         -- submitted
    closed_at TEXT
);
CREATE TABLE IF NOT EXISTS sub_requests (
    id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL REFERENCES tickets(id),
    desk TEXT NOT NULL,
    payload TEXT NOT NULL,
    assigned TEXT NOT NULL,
    notes TEXT NOT NULL,
    status TEXT NOT NULL,             -- pending | approved | changes_requested | rejected
    decided_by TEXT,
    decided_at TEXT,
    reason TEXT,
    desk_ref TEXT,                    -- reference from the desk's own system (via n8n)
    version INTEGER DEFAULT 1,        -- goes up each time the participant fixes this part
    submitted_at TEXT,                -- when this version reached the desk (the SLA clock starts here)
    sla_state TEXT DEFAULT '',        -- '' | reminded | escalated
    assigned_to TEXT                  -- officer the supervisor reassigned it to
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT,
    sub_id TEXT,
    type TEXT NOT NULL,
    at TEXT NOT NULL,
    detail TEXT
);
CREATE TABLE IF NOT EXISTS rule_overrides (
    desk TEXT NOT NULL,               -- a desk, or cross_desk
    rule_id TEXT NOT NULL,            -- a check id, or sla / params
    key TEXT NOT NULL,
    value TEXT NOT NULL,              -- JSON
    changed_by TEXT,
    changed_at TEXT,
    PRIMARY KEY (desk, rule_id, key)
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,             -- e.g. last_ticket: survives "Reset demo", so ticket ids are never reused
    value TEXT
);
CREATE TABLE IF NOT EXISTS hist_requests (
    request_id TEXT PRIMARY KEY,
    participant_type TEXT, pavilion TEXT, request_type TEXT, desks TEXT, submitted_at TEXT,
    legacy_hours REAL, munjiz_hours REAL,
    legacy_first_time INTEGER, munjiz_first_time INTEGER,
    legacy_participant_minutes REAL, munjiz_participant_minutes REAL,
    legacy_forms INTEGER,
    cross_desk_conflict INTEGER
);
CREATE TABLE IF NOT EXISTS hist_steps (
    request_id TEXT, desk TEXT, process TEXT, wait_hours REAL, reworked INTEGER
);
"""

# Columns added after the first version: databases created earlier get them on connect.
MIGRATIONS = {
    "tickets": {"conflicts_caught": "INTEGER DEFAULT 0"},
    "sub_requests": {"desk_ref": "TEXT", "version": "INTEGER DEFAULT 1", "submitted_at": "TEXT",
                     "sla_state": "TEXT DEFAULT ''", "assigned_to": "TEXT"},
    "hist_requests": {"cross_desk_conflict": "INTEGER"},
}


def _migrate(conn):
    for table, columns in MIGRATIONS.items():
        have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        for name, decl in columns.items():
            if name not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


_ready: set = set()  # database paths whose schema is already in place in this process


@contextmanager
def connect():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    key, existed = str(config.DB_PATH), config.DB_PATH.exists()
    conn = sqlite3.connect(config.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    if key not in _ready or not existed:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(SCHEMA)
        _migrate(conn)
        _ready.add(key)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def log(conn, type_: str, at: str, ticket_id=None, sub_id=None, **detail):
    conn.execute("INSERT INTO events (ticket_id, sub_id, type, at, detail) VALUES (?,?,?,?,?)",
                 (ticket_id, sub_id, type_, at, json.dumps(detail, ensure_ascii=False)))


def row(r: sqlite3.Row) -> dict:
    d = dict(r)
    for k in ("payload", "assigned", "notes", "conversation", "detail"):
        if isinstance(d.get(k), str):
            d[k] = json.loads(d[k])
    return d
