# Expo 2025 Osaka, Kansai dataset

Real figures from the last World Expo (13 Apr – 13 Oct 2025), used by `munjiz/osaka.py` for the replay test,
the organiser dashboard and the "Osaka case" demo buttons.

| File | Rows | What |
|---|---|---|
| `national_days.csv` | 163 | Every National or Special Day: date, Expo day, participant, pavilion type, and the organiser's own post for that day |
| `daily_attendance.csv` | 184 | Visitors per day, split into staff and contractor entries (site passes) and general visitors |
| `pavilions.csv` | 146 | Participants with their pavilion type (self-built Type A/X or a shared Commons building) and zone |

Checks: staff entries add up to the organiser's final 3,438,938; visitors to within 2 of 25,578,986.

Built by `scripts/osaka2025_build.py` from pinned Wikipedia revisions (ja 111389711 and 111387846, en 1380161384),
whose figures come from the organiser (expo2025.or.jp). Wikipedia text is CC BY-SA 4.0. Not in the sources, so
generated in the replay: the wording of each request, plates, crew names and IDs.
