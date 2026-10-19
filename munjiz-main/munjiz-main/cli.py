"""Scenario A in the terminal: chat, confirm, submit, then approve as each desk.

python cli.py            # interactive
python cli.py --demo     # scripted English run
python cli.py --demo-ar  # scripted Arabic run
"""
import sys

from munjiz import tickets
from munjiz.agent import run_turn
from munjiz.config import now
from munjiz.i18n import t

PAVILION = "France Pavilion"
SCRIPTS = {
    "--demo": [
        "I need to bring display equipment into our pavilion tomorrow at 10 pm. Two workers will come with the truck, and the screens need extra power.",
        "Plate is ABC 1234. Workers: Ahmed Ali, ID 1023456789 and John Smith, passport P1234567. The screens need 40 kW.",
        "yes",
    ],
    "--demo-ar": [
        "أحتاج إدخال معدات عرض إلى جناحنا بكرة الساعة 10 مساءً. بيجي عاملين مع الشاحنة، والشاشات تحتاج كهرباء إضافية.",
        "لوحة الشاحنة أ ب ج 1234. العمال: محمد العتيبي هوية 1023456789، وخالد الشمري هوية 2098765432. والشاشات تحتاج 40 كيلوواط.",
        "نعم",
    ],
}
YES = {"yes", "y", "confirm", "submit", "نعم", "اي", "أيوه", "ايوه", "تمام", "أكد", "ارسل", "أرسل"}


def main():
    script = SCRIPTS.get(sys.argv[1]) if len(sys.argv) > 1 else None
    conversation, result, started = [], None, now()
    while True:
        text = script.pop(0) if script else input("\nYou: ").strip()
        if script is not None:
            print(f"\nYou: {text}")
        if not text:
            continue
        if result and result.ready and text.lower() in YES:
            tid = tickets.submit(result, PAVILION, "Demo participant", conversation, started_at=started)
            print("\nMunjiz:", t("submitted", result.language, ticket=tid))
            break
        conversation.append({"role": "user", "content": text})
        result = run_turn(conversation, PAVILION)
        conversation.append({"role": "assistant", "content": result.reply})
        print("\nMunjiz:", result.reply)

    print("\n--- Desk staff ---")
    ticket = tickets.get_ticket(tid)
    for sub in ticket["subs"]:
        ticket = tickets.decide(sub["id"], True, f"{sub['desk']}.officer")
        print(f"{sub['id']:<10} approved by {sub['desk']}.officer  → ticket {ticket['status']}")


if __name__ == "__main__":
    main()
