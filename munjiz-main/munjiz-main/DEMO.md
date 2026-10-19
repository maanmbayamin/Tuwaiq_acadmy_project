# Demo run-of-show (1:50 – 3:30 in the pitch)

**Setup before going on stage**
- `scripts/start.sh` (n8n + API + app), one browser window full screen at 1366 px or wider, zoom 100%.
- Sign in → **Demo accounts (prototype)** → **France** (or type the pavilion code `FRA-2030`). The live-demo page
  shows two phones: the participant's Expo app on the left, Expo Admin on a desk officer's phone on the right,
  and the agent trace beside them. (Presenter settings → "Show the Expo Admin phone" turns the right phone off.)
- Clear old tickets: in a second tab sign in as **Organiser** → Ticket tracker → Reset demo. Ticket numbers keep
  counting after a reset (they are never reused), so the demo ticket is simply the next number.
- After a server restart everyone signs in again unless `MUNJIZ_API_TOKEN` is set in `.env`.
- Optional: n8n at http://localhost:5678 → Executions, to show the workflow runs live.
- Backup video ready in case the laptop fails.

| Time | On screen | Say |
|---|---|---|
| 0:00 | Both phones, empty | "Two sides, one ticket. Left: France's pavilion team in the Expo 2030 Riyadh app. Right: an Expo Admin desk officer. Today one request means three desks and three forms." |
| 0:10 | **1. Request** | "They just say it, in English or Arabic." |
| 0:20 | Cards turn amber; trace steps 1–4 | "Munjiz split it into three desks, checked 17 desk rules and 4 clash checks in code, and asks **once** for the plate, the IDs and the kW." |
| 0:35 | **2. Answer** → three Ready parts → **Confirm and send to 3 desks** on the left phone | "Gate L2 and a night slot, contractor passes, a 63 A outlet. One ticket." |
| 0:45 | Right phone: banner "New ticket…", all three desks show 1 | "The moment they confirm, each desk has its part, already checked against its rules and the other desks' parts. n8n routed it to each desk's system." |
| 0:55 | Right phone → **Accreditation** → the part → **Send back** → "John Smith's ID could not be verified" | "A person decides. Here one passport needs fixing." |
| 1:05 | Right phone: **Logistics** → Approve, **Utilities** → Approve | "The other desks approve. Watch the participant's ticket on the left." |
| 1:10 | Left phone: Munjiz says which part came back; ticket **Partially approved** | "The approvals stay. Munjiz asks for that part only." |
| 1:15 | **Fix: new passport** → **Send the fix** on the left phone | "Only the security part goes back, as version 2, on the same ticket." |
| 1:25 | Right phone: Accreditation shows v2 → **Approve**; left phone: **Done** | "One request, one ticket, done, even with a correction." |
| 1:35 | **New request** → **Clash demo** | "Every desk says yes on its own, but the truck may only come at night and the utility crews stop at 23:00. Munjiz catches the clash before any desk wastes time, and suggests the fix." Tap **Apply the suggested fix**, then **Confirm and send to 3 desks**. Leave this second ticket pending: the SLA step uses it. |

Then (3:30 – 4:05):
- **SLA:** sign in as **Supervisor** → SLA & escalations → open **Presenter control · SLA demo** at the bottom →
  **⏩ +300 min** (it ages every part still waiting, i.e. the clash ticket's three parts). Within 3 seconds the
  Logistics and Facilities parts appear under **Escalated to you** (their target is 120 min, escalation 240) and the
  Security part under **Reminder sent to the desk** (240 / 480). "Each desk has a response target. Late parts get
  a reminder, then reach the supervisor, who can reassign or decide." Optionally **👤 Reassign** one part.
  (Nothing to show here if no ticket is waiting: the step needs the pending clash ticket from 1:35.)
- **Organiser dashboard**: the before→after cards, SLA breaches by desk, clashes caught, then "What the last World Expo
  tells us" (real Osaka 2025 figures: 607,131 site passes, 3 of 42 self-built pavilions on schedule), then the "At
  Expo 2030 Riyadh scale" numbers. Say clearly that the request timings are simulated; the Osaka figures and the 197
  expected participants are public.
- (optional) **Desk rules**: "Organisers change a rule here, with no code, and every change is logged."

**Starting over in the participant window:** **New request** (or the phone's Home → New request) always starts
a fresh request, even while another ticket waits for a fix. To go back to a ticket a desk sent back, use
**↪ Continue fixing MNJ-…** under the demo scripts, or the phone's Requests tab → the ticket → **Fix this request**.
Right after sign-in Munjiz reopens a ticket that waits for a fix once, by itself.

**If anything fails on stage:** the offline parser needs no internet. If the app itself fails, switch to the
backup video and keep talking.
