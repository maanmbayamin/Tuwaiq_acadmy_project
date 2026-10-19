"""Expo 2030 Riyadh context: public facts (with sources), phases, participants.

Facts are public figures checked on 2026-10-13. Desk rules, gates and plots in this prototype are SIMULATED,
modelled on how World Expos usually run participant services; swap in Expo 2030 Riyadh's Special
Regulations and site plan when the organisers share them.
"""
from datetime import date, datetime

NAME = {"en": "Expo 2030 Riyadh", "ar": "إكسبو 2030 الرياض"}
THEME = "The Era of Change: Together for a Foresighted Tomorrow"  # English only; no official Arabic wording checked
OPENS = date(2030, 10, 1)
CLOSES = date(2031, 3, 31)
DAYS = (CLOSES - OPENS).days + 1  # 182

FACTS = {
    "expected_participating_countries": 197,  # organisers' expectation (Swiss Federal Council notice, Apr 2026)
    "expected_visits_millions": 42,           # BIE estimate
    "site_km2": 6,                            # ~6 km² site north of Riyadh, near King Khalid International Airport
}
SOURCES = [
    ("BIE: Expo 2030 Riyadh", "https://www.bie-paris.org/site/en/2030-riyadh"),
    ("Swiss Federal Council: participation decision", "https://www.admin.ch/en/newnsb/U5jT34vgqmGSHnWNihoPw"),
    ("Expo 2030 Riyadh news hub", "https://www.expo2030riyadh.sa/news-hub/commissioner-general-expo-2030-riyadh-heads-saudi-delegation-bie-paris"),
]

# The last World Expo (Expo 2025 Osaka, Kansai) and the last one in the Gulf (Expo 2020 Dubai). Public figures,
# checked on 2026-10-15. They anchor the dashboard's volumes in what really happened; none of this is Riyadh data.
OSAKA_2025 = {
    "days": 184,                          # 13 Apr - 13 Oct 2025
    "participants": 158,                  # countries and regions
    "international_orgs": 7,
    "visitors_millions": 29.02,
    "self_built_countries": 52,           # 47 Type A + 5 Type X; the other countries shared Commons pavilions
    "type_a_pavilions": 42,
    "built_on_time": 3,                   # international pavilions finished by 27 Dec 2024 (target: mid-Oct 2024)
    "type_a_done_before_opening": 39,     # by 11 Apr 2025, two days before opening
    "not_ready_opening_day": 5,           # Nepal, India, Vietnam, Brunei, Chile on 13 Apr 2025
    "last_pavilion_days_late": 97,        # the last pavilion opened on 19 Jul 2025
    "unpaid_construction_reports": 11,    # reported to the Expo Association by Aug 2025
    "site_passes": 607_131,               # AD passes issued to staff and contractors
    "site_passes_day": 381_534,
    "site_passes_permanent": 143_372,
    "site_passes_site_access": 82_225,
}
DUBAI_2020 = {
    "days": 182,
    "participants": 192,                  # countries
    "multilateral_orgs": 14,
    "visits_millions": 24.1,
}
PRECEDENT_SOURCES = [
    ("Expo 2025 Osaka, Kansai in data (organiser)", "https://www.expo2025.or.jp/en/expo_data/"),
    ("Expo 2025 pavilions (construction and opening dates)", "https://en.wikipedia.org/wiki/Expo_2025_pavilions"),
    ("Japan Today: unpaid pavilion subcontractors", "https://japantoday.com/category/features/kuchikomi/Osaka-Expo-building-subcontractors-royally-stiffed-by-deadbeat-clients"),
    ("Dubai Media Office: Expo 2020 Dubai closing figures", "https://mediaoffice.ae/en/news/2022/April/02-04/Dubai-delivers-on-promise-recording-over-24-million-visits-at-Expo-2020-Dubai"),
]

# Who files requests. Countries listed have publicly confirmed or signed participation (2026);
# the organisation and corporate entries are placeholders.
PARTICIPANTS = {
    "France Pavilion": "Official participant · Country",
    "Bahrain Pavilion": "Official participant · Country",
    "Oman Pavilion": "Official participant · Country",
    "Switzerland Pavilion": "Official participant · Country",
    "International Organisation Pavilion (example)": "Official participant · International organisation",
    "Corporate Pavilion (example)": "Non-official participant · Company",
}
ROLES = ["Pavilion director", "Commissioner General's office", "Pavilion operations lead",
         "Contractor for the pavilion"]


def phase(when: datetime | date) -> str:
    d = when.date() if isinstance(when, datetime) else when
    if d < OPENS:
        return "build_up"
    return "operations" if d <= CLOSES else "dismantling"


PHASE_LABEL = {
    "build_up": {"en": "Build-up", "ar": "مرحلة التجهيز"},
    "operations": {"en": "Open to visitors", "ar": "مفتوح للزوار"},
    "dismantling": {"en": "Dismantling", "ar": "مرحلة التفكيك"},
}


def expo_day(when: datetime) -> int | None:
    return (when.date() - OPENS).days + 1 if phase(when) == "operations" else None
