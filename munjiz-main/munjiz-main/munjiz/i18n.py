import re
from datetime import datetime

_ARABIC = re.compile(r"[؀-ۿ]")
_LATIN = re.compile(r"[A-Za-z]")

AR_WEEKDAYS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
AR_MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
             "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]


def detect_lang(text: str) -> str:
    return "ar" if len(_ARABIC.findall(text)) > len(_LATIN.findall(text)) else "en"


def fmt_dt(value: str | datetime | None, lang: str) -> str:
    if not value:
        return "—"
    dt = datetime.fromisoformat(value) if isinstance(value, str) else value
    if lang == "ar":
        hour = dt.hour % 12 or 12
        period = "مساءً" if dt.hour >= 12 else "صباحًا"
        return f"{AR_WEEKDAYS[dt.weekday()]} {dt.day} {AR_MONTHS[dt.month - 1]}، {hour}:{dt.minute:02d} {period}"
    return dt.strftime("%a %d %b, %H:%M")


# Agent replies and UI labels.
T = {
    "followup_intro": {
        "en": "Almost there. To send this to all desks in one go, I need:",
        "ar": "باقي القليل. حتى أرسل الطلب لجميع الجهات دفعة واحدة، أحتاج:",
    },
    "problems_intro": {
        "en": "A few things need changing before I can submit:",
        "ar": "هناك أمور تحتاج تعديلًا قبل الإرسال:",
    },
    "summary_intro": {
        "en": "Here's what I'll submit under **one ticket**:",
        "ar": "هذا ما سأرسله تحت **تذكرة واحدة**:",
    },
    "summary_outro": {
        "en": "Shall I submit it?",
        "ar": "هل أرسله؟",
    },
    "nothing_understood": {
        "en": "I can handle deliveries, worker permits and power or facility requests for your pavilion. What do you need?",
        "ar": "أستطيع ترتيب التوصيلات وتصاريح العمال وطلبات الكهرباء والمرافق لجناحك. ماذا تحتاج؟",
    },
    "for_workers": {"en": "{n} workers", "ar": "عددهم {n}"},
    "submitted": {
        "en": "Submitted. Your ticket is **{ticket}**. Each desk reviews its part and you'll see every approval here.",
        "ar": "تم الإرسال. رقم تذكرتك **{ticket}**. كل جهة تراجع الجزء الخاص بها وستظهر الموافقات هنا.",
    },
    "staff_note": {"en": "Note for desk", "ar": "ملاحظة للجهة"},
    "conflicts_intro": {
        "en": "Each desk's part is fine on its own, but they clash with each other:",
        "ar": "كل جزء سليم بمفرده، لكن الأجزاء تتعارض مع بعضها:",
    },
    "suggested_fix": {"en": "Suggested fix", "ar": "الحل المقترح"},
    "apply_fix_question": {
        "en": "Shall I apply the suggested fix?",
        "ar": "هل أطبّق الحل المقترح؟",
    },
    "apply_fix_action": {"en": "Apply the suggested fix", "ar": "طبّق الحل المقترح"},
    "fix_applied": {
        "en": "Done. I applied the fix and checked every desk again.",
        "ar": "تم. طبّقت الحل وأعدت التحقق من جميع الجهات.",
    },
    "part_returned": {
        "en": "**{desk}** sent its part ({sub}) back: “{reason}”\n\nSend me the corrected details for this part only. "
              "The other parts stay as they are{approved}.",
        "ar": "أعادت **{desk}** الجزء الخاص بها ({sub}): «{reason}»\n\nأرسل لي التفاصيل المصححة لهذا الجزء فقط، "
              "وتبقى الأجزاء الأخرى كما هي{approved}.",
    },
    "approved_kept": {"en": " ({n} already approved)", "ar": " ({n} تمت الموافقة عليها)"},
    "fix_summary_intro": {
        "en": "Here's the corrected part. Only this goes back to the desk:",
        "ar": "هذا الجزء بعد التصحيح، وهو فقط ما سيعود للجهة:",
    },
    "fix_summary_intro_many": {
        "en": "Here are the corrected parts. Only these go back to their desks:",
        "ar": "هذه الأجزاء بعد التصحيح، وهي فقط ما سيعود للجهات:",
    },
    "fix_still_outstanding": {
        "en": "Still waiting for your fix: **{desk}** ({sub}) asked: “{reason}”. That part stays with you until you "
              "send its correction.",
        "ar": "ما زال ينتظر تصحيحك: طلبت **{desk}** ({sub}): «{reason}». يبقى هذا الجزء لديك حتى ترسل تصحيحه.",
    },
    "fix_locked": {
        "en": "Fixing this would mean changing the {desk} part ({sub}), and that part isn't open for changes now. "
              "Choose details that fit it, or ask that desk to send its part back.",
        "ar": "حل هذا يتطلب تعديل جزء {desk} ({sub})، وهذا الجزء غير مفتوح للتعديل الآن. "
              "اختر تفاصيل تتوافق معه، أو اطلب من تلك الجهة إعادة جزئها.",
    },
    "fix_whose_id": {
        "en": "I couldn't tell whose ID {id} is. Please send it with the worker's name.",
        "ar": "لم أعرف لمن رقم الهوية {id}. أرسله مع اسم العامل من فضلك.",
    },
    "workers_added": {
        "en": "Note: this adds {names}, so the request now has {n} workers (it had {before}). If someone replaces a "
              "worker, tell me who.",
        "ar": "ملاحظة: هذا يضيف {names}، فيصبح عدد العمال {n} (كان {before}). إذا كان أحدهم بديلًا لعامل آخر فأخبرني من.",
    },
    "workers_replaced": {
        "en": "Note: this replaces {old} with {new}. The request has {n} workers.",
        "ar": "ملاحظة: هذا يستبدل {old} بـ {new}. عدد العمال في الطلب {n}.",
    },
    "workers_removed": {
        "en": "Note: this removes {names}, so the request now has {n} workers (it had {before}).",
        "ar": "ملاحظة: هذا يحذف {names}، فيصبح عدد العمال {n} (كان {before}).",
    },
    "fix_summary_outro": {"en": "Shall I send it?", "ar": "هل أرسله؟"},
    "fix_nothing_changed": {
        "en": "I couldn't find a change for that part yet. The desk asked: {reasons}",
        "ar": "لم أجد تعديلًا على هذا الجزء بعد. طلب الجهة: {reasons}",
    },
    "fix_this_request": {"en": "Fix this request", "ar": "أصلح هذا الطلب"},
    "fix_sent": {
        "en": "Sent. **{desk}** reviews the corrected part ({sub}, version {version}) on the same ticket **{ticket}**.",
        "ar": "تم الإرسال. تراجع **{desk}** الجزء المصحح ({sub}، النسخة {version}) على التذكرة نفسها **{ticket}**.",
    },
}


def t(key: str, lang: str, **kw) -> str:
    return T[key][lang].format(**kw)
