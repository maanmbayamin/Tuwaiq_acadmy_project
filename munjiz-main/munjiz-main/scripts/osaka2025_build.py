"""Build the Expo 2025 Osaka, Kansai dataset in datasets/osaka2025/ from pinned Wikipedia revisions.

Wikipedia is the parser's source; the facts in it come from the organiser (each National Day row links to the
official expo2025.or.jp blog post for that day; attendance comes from the organiser's daily releases).
Text from Wikipedia is CC BY-SA 4.0. Needs network and pycountry (build time only):

    python3 -m pip install pycountry
    python3 scripts/osaka2025_build.py
"""
import csv
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import pycountry

OUT = Path(__file__).resolve().parent.parent / "datasets" / "osaka2025"
OPENS = date(2025, 4, 13)
PAGES = {  # pinned revisions, retrieved 2026-10-15
    "expo": ("ja", 111389711, "2025年日本国際博覧会"),
    "history": ("ja", 111387846, "大阪・関西万博の歴史"),
    "pavilions": ("en", 1380161384, "Expo 2025 pavilions"),
}
NON_ISO = {"ASEAN": "ASEAN", "BIE": "Bureau International des Expositions", "IFRC": "IFRC (Red Cross and Red Crescent)",
           "ISTC": "International Science and Technology Center", "ITER": "ITER Organization",
           "UN": "United Nations", "KOS": "Kosovo"}
NAME_FIX = {"Korea": "KOR", "South Korea": "KOR", "Republic of Korea": "KOR", "Kosovo": "KOS", "Palestine": "PSE",
            "Vatican City": "VAT", "Holy See": "VAT", "Turkey": "TUR", "Türkiye": "TUR", "Micronesia": "FSM",
            "Federated States of Micronesia": "FSM", "Laos": "LAO", "Russia": "RUS", "Iran": "IRN", "Syria": "SYR",
            "Bolivia": "BOL", "Tanzania": "TZA", "Moldova": "MDA", "Vietnam": "VNM", "Brunei": "BRN",
            "Democratic Republic of the Congo": "COD", "Republic of the Congo": "COG", "Ivory Coast": "CIV",
            "Côte d'Ivoire": "CIV", "Cape Verde": "CPV", "East Timor": "TLS", "Timor-Leste": "TLS",
            "United States": "USA", "United Kingdom": "GBR", "Czech Republic": "CZE", "Eswatini": "SWZ",
            "São Tomé and Príncipe": "STP", "Sao Tome and Principe": "STP", "The Gambia": "GMB", "Gambia": "GMB",
            "Taiwan": "TWN", "St. Kitts and Nevis": "KNA", "St. Lucia": "LCA"}


def fetch(key: str) -> str:
    lang, rev, _ = PAGES[key]
    url = f"https://{lang}.wikipedia.org/w/index.php?" + urllib.parse.urlencode({"oldid": rev, "action": "raw"})
    req = urllib.request.Request(url, headers={"User-Agent": "munjiz-hackathon/1.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8")


def name_of(code: str) -> str:
    if code in NON_ISO:
        return NON_ISO[code]
    c = pycountry.countries.get(alpha_3=code)
    return getattr(c, "common_name", None) or c.name


def iso3(name: str) -> str:
    name = name.strip()
    if name in NAME_FIX:
        return NAME_FIX[name]
    try:
        return pycountry.countries.lookup(name).alpha_3
    except LookupError:
        return ""


def national_days(text: str) -> list[dict]:
    a = text.index("== ナショナルデー・スペシャルデー一覧 ==")
    table = re.sub(r"<!--.*?-->", "", text[a:text.index("\n|}", a)], flags=re.S)  # drops moved/cancelled days
    rows = []
    for row in table.split("\n|-")[1:]:
        lines = [line for line in row.strip().split("\n") if line.startswith("|")]
        m = re.match(r"\|(\d+)日", lines[0]) if lines else None
        if not m:
            continue
        for month, cell in zip(range(4, 11), lines[1:]):
            for code in re.findall(r"<small>([^<]+)</small>", cell):
                d = date(2025, month, int(m.group(1)))
                src = re.search(r"url=(https://www\.expo2025\.or\.jp/officialblog/[^|}\s]+)", cell)
                code = code.strip()
                rows.append({"osaka_date": d.isoformat(), "expo_day": (d - OPENS).days + 1, "code": code,
                             "participant": name_of(code),
                             "kind": "organisation" if code in NON_ISO and code != "KOS" else "country",
                             "source": src.group(1) if src else ""})
    return sorted(rows, key=lambda r: r["osaka_date"])


def attendance(text: str) -> list[dict]:
    a = text.index("=== 入場者数の詳細情報 ===")
    table = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", text[a:text.index("\n|}", a)], flags=re.S)
    num = lambda c: int(re.sub(r"[^\d]", "", c.split("|")[-1]) or 0)  # noqa: E731 (cells may carry a style prefix)
    rows, started = [], False
    for row in table.split("\n|-"):
        lines = row.strip().split("\n")
        m = re.fullmatch(r"!(\d+)", lines[0].strip()) if lines else None
        if not m:
            continue
        cells = [c[1:].strip() for c in lines[1:] if c.startswith("|")]
        md = re.match(r"(\d+)月(\d+)日", re.sub(r"<[^>]+>", "", cells[0]))
        d = date(2025, int(md.group(1)), int(md.group(2)))
        started = started or d == OPENS  # skip the three test-run days before opening
        if started:
            rows.append({"expo_day": int(m.group(1)), "date": d.isoformat(), "total": num(cells[1]),
                         "staff_entries": num(cells[2]), "general": num(cells[3])})
    return rows


def pavilions(text: str) -> list[dict]:
    def section(start: str, end: str) -> str:
        return text[text.index(start):text.index(end)]

    rows = []
    for block in section("== Type A or X pavilions ==", "== Type C pavilions ==").split("\n|-")[1:]:
        zone = re.search(r"\{\{Not yet\|color=[^|]*\|([^}]+)\}\}", block)
        for name in re.findall(r"\{\{[Ff]lagcountry\|([^}|]+)", block):
            rows.append({"participant": name.strip(), "code": iso3(name), "pavilion": "Self-built (Type A/X)",
                         "zone": zone.group(1).strip() if zone else ""})
    commons = section("== Type C pavilions ==", "== International organizations' pavilions ==")
    parts = re.split(r"\n=== (Commons [A-Z]) ===", commons)
    for label, body in zip(parts[1::2], parts[2::2]):
        for name in re.findall(r"\{\{[Ff]lagcountry\|([^}|]+)", body):
            rows.append({"participant": name.strip(), "code": iso3(name), "pavilion": label, "zone": ""})
    return rows


def write(name: str, rows: list[dict]):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{name}: {len(rows)} rows")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    expo, history, pav = fetch("expo"), fetch("history"), fetch("pavilions")
    days, daily, pavs = national_days(history), attendance(expo), pavilions(pav)
    types = {p["code"]: p["pavilion"] for p in pavs if p["code"]}
    for d in days:
        d["pavilion"] = types.get(d["code"], "International organisation" if d["kind"] == "organisation" else
                                  "Not listed")  # the pavilions article has no row for a few countries
    assert len(daily) == 184, len(daily)
    # Final totals: 3,438,938 staff entries and 25,578,986 visitors; the daily releases add up to 2 fewer visitors.
    assert sum(r["staff_entries"] for r in daily) == 3_438_938, "staff entries do not match the organiser's total"
    assert abs(sum(r["general"] for r in daily) - 25_578_986) <= 10, "attendance does not match the organiser's total"
    write("national_days.csv", days)
    write("daily_attendance.csv", daily)
    write("pavilions.csv", pavs)
    unmatched = [p["participant"] for p in pavs if not p["code"]]
    if unmatched:
        print("no ISO code for:", ", ".join(unmatched), file=sys.stderr)


if __name__ == "__main__":
    main()
