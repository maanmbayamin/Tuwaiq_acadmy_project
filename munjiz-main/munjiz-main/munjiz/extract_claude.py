"""Claude extractor: one tool per desk; Claude calls each desk that the request touches.

Claude only extracts. Splitting, rule checks and follow-up questions stay in code.
Responses are cached by transcript so a rehearsed demo replays with no API call.
"""
import hashlib
import json
from datetime import datetime

from .config import CACHE_DIR, CLAUDE_MODEL

DT = {"type": "string", "description": "ISO 8601 with +03:00 offset, e.g. 2026-10-14T22:00:00+03:00"}

TOOLS = [
    {
        "name": "logistics_request",
        "description": "Book a gate slot and delivery route for a vehicle bringing goods or equipment to the pavilion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cargo_description": {"type": "string", "description": "What is being delivered, in the participant's words."},
                "vehicle_type": {"type": "string", "enum": ["van", "light_truck", "heavy_truck"],
                                 "description": "'truck'/'lorry'/'شاحنة' with no size given means heavy_truck; pickup/دينا/ونيت is light_truck."},
                "vehicle_plate": {"type": "string"},
                "arrival_datetime": DT,
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "security_request",
        "description": "Temporary access permits for workers coming on site.",
        "input_schema": {
            "type": "object",
            "properties": {
                "worker_count": {"type": "integer"},
                "workers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"full_name": {"type": "string"}, "id_number": {"type": "string"}},
                        "required": ["full_name", "id_number"],
                        "additionalProperties": False,
                    },
                    "description": "Only workers whose name AND ID/passport number were given.",
                },
                "access_datetime": DT,
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "facilities_request",
        "description": "Extra power connection for the pavilion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "enum": ["power_connection"]},
                "power_kw": {"type": "number"},
                "needed_from": DT,
            },
            "required": ["service"],
            "additionalProperties": False,
        },
    },
]

TOOL_DESK = {"logistics_request": "logistics", "security_request": "security", "facilities_request": "facilities"}

SYSTEM = """You are Munjiz, the request intake agent for Expo 2030 Riyadh participants (pavilion teams and their contractors).
Read the conversation and call every desk tool the participant's request needs, once each, all in one turn.
Fill only what the participant actually said. Leave out any field they did not give; never guess plate numbers, names, IDs or kW.
Resolve relative dates ("tomorrow at 10 pm", "بكرة الساعة 10 مساءً") against the current time given below, in Riyadh time.
If the participant corrects something later in the conversation, use the latest value.
Do not write any reply text; the app writes the reply."""


def _cache_path(transcript: str):
    return CACHE_DIR / (hashlib.sha256(f"{CLAUDE_MODEL}\n{transcript}".encode()).hexdigest()[:24] + ".json")


def extract(conversation: list[dict], pavilion: str, now: datetime) -> dict:
    transcript = "\n".join(f"{'Participant' if m['role'] == 'user' else 'Munjiz'}: {m['content']}" for m in conversation)
    path = _cache_path(transcript)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    import anthropic

    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low"},
        system=SYSTEM,
        tools=TOOLS,
        tool_choice={"type": "auto"},
        messages=[{"role": "user", "content": f"Current time: {now.isoformat()}\nPavilion: {pavilion}\n\nConversation:\n{transcript}"}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined the request")

    out = {"logistics": None, "security": None, "facilities": None}
    for block in response.content:
        if block.type == "tool_use" and block.name in TOOL_DESK:
            desk = TOOL_DESK[block.name]
            out[desk] = {**(out[desk] or {}), **{k: v for k, v in dict(block.input).items() if v not in (None, "")}}

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
