"""Offline extractor: regex rules for English and Gulf/Standard Arabic.

Free and deterministic, so the demo works with no API key or internet.
It covers the demo scenarios, not every phrasing; the Claude backend handles open-ended input.
"""
import re
from datetime import datetime, timedelta

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

EN_NUM = {"a": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
          "seven": 7, "eight": 8, "nine": 9, "ten": 10}
AR_NUM = {"واحد": 1, "اثنين": 2, "اثنان": 2, "إثنين": 2, "ثلاث": 3, "ثلاثة": 3, "أربع": 4, "أربعة": 4,
          "اربع": 4, "اربعة": 4, "خمس": 5, "خمسة": 5, "ست": 6, "ستة": 6, "سبع": 7, "سبعة": 7}

# Longest phrases first so "day after tomorrow" wins over "tomorrow".
DAY_WORDS = [("day after tomorrow", 2), ("بعد بكرة", 2), ("بعد بكره", 2), ("بعد غد", 2),
             ("tomorrow", 1), ("بكرة", 1), ("بكره", 1), ("غدًا", 1), ("غداً", 1), ("غدا", 1), ("باكر", 1),
             ("tonight", 0), ("today", 0), ("الليلة", 0), ("اليوم", 0)]
EN_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
AR_WEEKDAYS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]

TIME_EN = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)(?![a-z])", re.I)
TIME_24 = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
TIME_AR = re.compile(r"(?<!\d)(\d{1,2})(?::(\d{2}))?\s*(مساءً|مساءا|مساء|بالليل|الليل|ليلاً|ليلا|العصر|الظهر|صباحًا|صباحا|صباح|الصبح|الفجر|م|ص)(?![ء-ي])")
AR_PM = ("مساء", "بالليل", "الليل", "ليل", "العصر", "الظهر", "م")

LOGISTICS_WORDS = re.compile(r"truck|lorry|trailer|van\b|pickup|deliver|bring|equipment|cargo|shipment|"
                             r"شاحن|تريلا|تريلة|دينا|ونيت|فان|توصيل|تسليم|إدخال|ادخال|معدات|بضاع|شحنة", re.I)
SECURITY_WORDS = re.compile(r"worker|technician|crew|installer|labou?rer|staff|"
                            r"عامل|عمال|فني|فنيين|طاقم|موظف", re.I)
FACILITIES_WORDS = re.compile(r"power|electric|socket|outlet|\bkw\b|kilowatt|"
                              r"كهرب|طاقة|كيلو\s?واط|كيلوواط|فيش", re.I)

HEAVY = re.compile(r"truck|lorry|trailer|شاحن|تريلا|تريلة", re.I)
LIGHT = re.compile(r"small truck|light truck|pickup|دينا|ونيت|شاحنة صغيرة|شاحنة خفيفة", re.I)
VAN = re.compile(r"\bvan\b|فان", re.I)

KW = re.compile(r"(\d+(?:\.\d+)?)\s*(?:kw|kilowatts?|كيلو\s?واط|كيلوواط|ك\.?و)", re.I)
PLATE_EN = re.compile(r"plate(?:\s*(?:number|no\.?|#))?\s*(?:is|:)?\s*([A-Z]{3}[\s-]?\d{1,4}|\d{1,4}[\s-]?[A-Z]{3})", re.I)
PLATE_AR = re.compile(r"(?:لوحة|اللوحة|لوحتها)\s*(?:الشاحنة|الشاحنه|السيارة|المركبة)?\s*(?:رقم|رقمها)?\s*[:：]?\s*"
                      r"((?:[ء-ي]\s?){1,3}\s?\d{1,4}|\d{1,4}\s?(?:[ء-ي]\s?){1,3}|[A-Z]{3}[\s-]?\d{1,4})")
PLATE_BARE = re.compile(r"\b([A-Z]{3}[\s-]?\d{3,4})\b")
ID_TOKEN = re.compile(r"\b([12]\d{9}|[A-Z]{1,2}\d{6,8})\b")

CARGO_EN = re.compile(r"\b(?:bring|deliver|move|send|ship)\s+(?:in\s+)?(?:our\s+|the\s+|some\s+)?(.{3,50}?)\s+(?:in)?to\b", re.I)
CARGO_AR = re.compile(r"(?:إدخال|ادخال|توصيل|إحضار|احضار|ندخل|نجيب|أدخل|ادخل)\s+(.{3,40}?)\s+(?:إلى|الى|في|لـ|ل)(?=\s|[ء-ي])")
CARGO_FALLBACK = [(re.compile(r"screens?|displays?", re.I), "Display screens"),
                  (re.compile(r"شاشات|شاشة"), "شاشات عرض"),
                  (re.compile(r"equipment", re.I), "Equipment"),
                  (re.compile(r"معدات"), "معدات")]

NAME_STOP = {"id", "iqama", "passport", "no", "no.", "number", "national", "and", "is", "his", "her", "name",
             "worker", "workers", "first", "second", "third", "the", "with", "of", "one", "two", "#",
             "رقم", "الهوية", "هوية", "هويته", "الإقامة", "إقامة", "اقامة", "إقامته", "جواز", "جوازه", "السفر",
             "اسمه", "العامل", "العمال", "الأول", "الاول", "الثاني", "الثالث", "و", "هو", "سجل", "مدني",
             "first:", "second:", "names", "الأسماء", "ids",
             # fix-loop filler: "Ahmed Ali's correct ID is …", "رقم هوية خالد الشمري الصحيح …"
             "correct", "corrected", "correction", "new", "updated", "update", "right", "fixed", "valid", "actual",
             "proper", "her", "their", "its", "are", "was", "should", "be", "now", "for", "to", "please", "add",
             "also", "plus", "here", "here's", "id's", "passport's",
             "الصحيح", "الصحيحة", "الصحيحه", "الصح", "صحيح", "الجديد", "الجديدة", "الجديده", "جديد", "المحدث",
             "المحدّث", "المعدل", "المعدّل", "رقمه", "رقمها", "هويتها", "جوازها", "إقامتها", "هي", "أضف", "اضف",
             "إضافة", "اضافة", "أيضا", "أيضًا", "كذلك", "هذا", "هذه"}

# Names that genuinely start with و, so the attached-"and" strip leaves them alone.
WAW_NAMES = {"وليد", "وائل", "وجدي", "وسام", "وفاء", "ولاء", "وضاح", "وديع", "وهيب", "وعد", "وداد", "وجدان", "ورد", "وصال"}


def _norm(text: str) -> str:
    return text.translate(_DIGITS)


def _day_offset(low: str, time_at: int) -> int | None:
    """The day word closest to the time: in "our National Day is the day after tomorrow; the truck comes tomorrow
    at 10 pm" the truck comes tomorrow. Longer phrases are matched first, so "tomorrow" inside "day after
    tomorrow" is not counted twice."""
    taken, found = [False] * len(low), []
    for word, days in DAY_WORDS:
        for hit in re.finditer(re.escape(word), low):
            if not any(taken[hit.start():hit.end()]):
                taken[hit.start():hit.end()] = [True] * len(word)
                found.append((min(abs(hit.start() - time_at), abs(hit.end() - time_at)), days))
    return min(found)[1] if found else None


def parse_datetime(text: str, now: datetime) -> str | None:
    low = text.lower()
    m = TIME_EN.search(low)
    hour = minute = None
    if m:
        hour, minute = int(m.group(1)) % 12, int(m.group(2) or 0)
        if m.group(3).startswith("p"):
            hour += 12
    elif (m := TIME_AR.search(text)):
        hour, minute = int(m.group(1)), int(m.group(2) or 0)
        if m.group(3).startswith(AR_PM) and hour < 12:
            hour += 12
        elif m.group(3) in ("الظهر",) and hour == 12:
            hour = 12
    elif (m := TIME_24.search(text)):
        hour, minute = int(m.group(1)), int(m.group(2))
    if hour is None:
        return None

    offset = _day_offset(low, m.start())
    if offset is None:
        for i, name in enumerate(EN_WEEKDAYS):
            if name in low:
                offset = (i - now.weekday()) % 7 or 7
        for i, name in enumerate(AR_WEEKDAYS):
            if name in text:
                offset = (i - now.weekday()) % 7 or 7
    day = now.date() + timedelta(days=offset or 0)
    dt = datetime(day.year, day.month, day.day, hour, minute, tzinfo=now.tzinfo)
    if offset is None and dt < now:
        dt += timedelta(days=1)
    return dt.isoformat()


def _worker_count(text: str) -> int | None:
    m = re.search(r"\b(\d+|" + "|".join(EN_NUM) + r")\s+(?:\w+\s+)?(?:workers|technicians|installers|crew members|labou?rers|people|men|staff)\b", text, re.I)
    if m:
        v = m.group(1).lower()
        return int(v) if v.isdigit() else EN_NUM[v]
    if re.search(r"\ba\s+(?:worker|technician)\b", text, re.I):
        return 1
    m = re.search(r"(\d+)\s*(?:من\s+)?(?:عمال|عامل|فنيين|فني|أشخاص|اشخاص)", text)
    if m:
        return int(m.group(1))
    m = re.search(r"(" + "|".join(AR_NUM) + r")\s+(?:من\s+)?(?:العمال|عمال|عامل|فنيين|أشخاص)", text)
    if m:
        return AR_NUM[m.group(1)]
    if re.search(r"عاملين|عاملان|فنيين اثنين|عاملَين", text):
        return 2
    if re.search(r"عامل واحد|فني واحد", text):
        return 1
    return None


def _workers(text: str) -> list[dict]:
    out, last_end = [], 0
    for m in ID_TOKEN.finditer(text):
        segment = re.split(r"[\n،,;؛.()\[\]:–—-]", text[last_end:m.start()])
        words = []
        for part in reversed(segment):
            words = [w for w in part.split() if re.sub(r"['’]s$", "", w).lower() not in NAME_STOP
                     and not (w.startswith("و") and w[1:] in NAME_STOP) and not any(c.isdigit() for c in w)]
            if words:
                break
        words = [re.sub(r"['’]s$", "", w) for w in words[-4:]]  # "Smith's passport" → Smith
        if words and len(words[0]) > 3 and words[0].startswith("و") and words[0] not in WAW_NAMES:
            words[0] = words[0][1:]  # "وخالد" → "خالد" (attached "and")
        out.append({"full_name": " ".join(words), "id_number": m.group(1)})
        last_end = m.end()
    return out


def _cargo(text: str, fallback: bool) -> str | None:
    if (m := CARGO_EN.search(text)) or (m := CARGO_AR.search(text)):
        return m.group(1).strip()
    for pat, label in CARGO_FALLBACK if fallback else []:
        if pat.search(text):
            return label
    return None


def _plate(text: str) -> str | None:
    m = PLATE_EN.search(text) or PLATE_AR.search(text) or PLATE_BARE.search(text)
    return re.sub(r"\s+", " ", m.group(1).upper().replace("-", " ")).strip() if m else None


def extract(user_messages: list[str], now: datetime) -> dict:
    """Merge every user message in order; later statements override earlier ones."""
    out = {"logistics": None, "security": None, "facilities": None}
    for raw in user_messages:
        text = _norm(raw)
        when = parse_datetime(text, now)

        if LOGISTICS_WORDS.search(text) or PLATE_EN.search(text) or PLATE_AR.search(text):
            d = out["logistics"] or {}
            vtype = "light_truck" if LIGHT.search(text) else "heavy_truck" if HEAVY.search(text) else "van" if VAN.search(text) else None
            for k, v in {"cargo_description": _cargo(text, fallback="cargo_description" not in d), "vehicle_type": vtype,
                         "vehicle_plate": _plate(text), "arrival_datetime": when}.items():
                if v is not None:
                    d[k] = v
            out["logistics"] = d
        elif out["logistics"] is not None and (plate := _plate(text)):
            out["logistics"]["vehicle_plate"] = plate

        workers = _workers(text)
        if SECURITY_WORDS.search(text) or workers:
            d = out["security"] or {}
            if (n := _worker_count(text)) is not None:
                d["worker_count"] = n
            if workers:
                known = {w["id_number"] for w in d.get("workers", [])}
                d["workers"] = d.get("workers", []) + [w for w in workers if w["id_number"] not in known]
            if when and not out["logistics"]:
                d["access_datetime"] = when
            out["security"] = d

        if FACILITIES_WORDS.search(text) or KW.search(text):
            d = out["facilities"] or {"service": "power_connection"}
            if (m := KW.search(text)):
                d["power_kw"] = float(m.group(1))
            if when and not out["logistics"]:
                d["needed_from"] = when
            out["facilities"] = d
    return out
