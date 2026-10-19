"""Participant chat decisions that don't need Streamlit, so they can be tested: which ticket the chat is on,
and whether a message is a short "yes, apply it"."""
import re

from . import tickets

YES = {"yes", "y", "confirm", "submit", "send", "ok", "okay", "sure", "نعم", "اي", "ايوه", "أيوه", "تمام", "أكد",
       "ارسل", "أرسل", "موافق"}
APPLY = {"apply", "fix", "طبق", "طبّق", "طبقه", "طبّقه", "طبقها", "طبّقها"}
FILLER = {"the", "suggested", "it", "that", "this", "please", "do", "go", "ahead", "yeah", "yep",
          "الحل", "المقترح", "الاقتراح", "من", "فضلك", "لو", "سمحت", "هذا", "ذلك"}


def _words(message: str) -> list[str]:
    return re.sub(r"[.!?,،؟]", " ", message.strip().lower()).split()


def is_yes(message: str) -> bool:
    return " ".join(_words(message)) in YES


def wants_fix(message: str) -> bool:
    """Accepting the suggested fix is a short confirmation ("yes", "apply it", "طبّق الحل المقترح"). Anything longer,
    or anything with a number in it, is new information and goes through the agent."""
    words = set(_words(message))
    if not words or len(_words(message)) > 4 or any(c.isdigit() for c in message):
        return False
    return bool(words & (YES | APPLY)) and words <= YES | APPLY | FILLER


def waiting_for_fix(pavilion: str) -> list[dict]:
    """This pavilion's tickets with a part a desk sent back, newest first."""
    return [t for t in tickets.list_tickets(pavilion) if t["status"] in ("partially_approved", "action_needed")]


def session_ticket(pavilion: str, ticket_id: str | None, auto_resume: bool) -> str | None:
    """The ticket the participant's chat is on. An id from another pavilion (or one that no longer exists) is
    dropped. With no ticket, the newest one waiting for a fix is picked up only when auto_resume is set
    (once per sign-in, never after the participant starts a new request)."""
    if ticket_id:
        return ticket_id if tickets.get_ticket_for(ticket_id, pavilion) else None
    if auto_resume and (waiting := waiting_for_fix(pavilion)):
        return waiting[0]["id"]
    return None
