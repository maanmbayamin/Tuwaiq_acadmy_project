# Munjiz · منجز

**One request. One ticket. Done.** A prototype for **Expo 2030 Riyadh**, challenge 5.5.

Expo 2030 Riyadh runs 1 Oct 2030 – 31 Mar 2031 on a ~6 km² site north of Riyadh, and organisers expect
197 participating countries ([BIE](https://www.bie-paris.org/site/en/2030-riyadh),
[Swiss Federal Council](https://www.admin.ch/en/newnsb/U5jT34vgqmGSHnWNihoPw)). Each participant's pavilion team
and its contractors deal with several service desks for everyday requests. Munjiz is their single window.

A participant describes a request once, in English or Arabic. Munjiz splits it into one sub-request per desk
(Logistics & Site Access, Accreditation & Security, Facilities & Utilities), checks each desk's rules in code, checks
the parts for clashes with each other, asks once for anything missing, shows a summary to confirm, and submits
everything under one ticket. Expo Admin desk staff approve, request a change or reject; a part that comes back is
fixed on its own while the approved parts stay approved. Supervisors watch response targets and organisers see the
impact on a dashboard.

## Project file

### 1. The challenge and the problem
**Challenge 5.5** (Track 5, Digital identity, services and commerce): *a participant struggles to complete a simple
request when it passes through three different service desks.*

A participant is a country, international organisation or company with a pavilion at the Expo, plus its staff and
contractors. One everyday request (bring equipment in at night, register workers, get extra power) touches
Logistics, Accreditation and Facilities. Each desk has its own form, rules and status, so the participant types the
same details three times, forms bounce back for missing information, clashes between desks are found late, and
organisers can't see where requests wait.

### 2. The solution and how it works
Munjiz is a single window with **two sides and one ticket between them**:
- **Participant side** (the Expo app, signed in with the pavilion code): describe the need once, answer one
  follow-up, accept a suggested fix if two desks' parts clash, confirm, and track one ticket. If a desk sends a part
  back, Munjiz asks for that part only.
- **Expo Admin side**: desk staff see only their desk's part, already checked; they approve, request a change or
  reject with a reason. The supervisor gets SLA reminders and escalations and can reassign or decide on a desk's
  behalf. Organisers see the dashboard, every event log, and change desk rules without code.

The AI only extracts. Rules, clash checks, follow-up questions and summaries are code, and a person always decides.
See the [workflow diagram](docs/workflow.html) and "How it works" below.

### 3. Technologies and tools
Python 3.11+ · Streamlit (participant app, desk console, supervisor, dashboard, rules pages) · Claude API with tool
use (or the free offline parser) · SQLite · YAML rule files · pandas + Plotly · Starlette API · n8n (routes each part
to desk systems, notifications, SLA watchdog) · Docker for n8n · pytest (59 tests).

### 4. Expected impact and fit with Expo 2030 Riyadh
On simulated data (labelled as such everywhere): time to complete a request 24.6 h → 3.0 h, participant effort
44 → 4 minutes, complete first time 39% → 88%, desk reviews over target 92% → 26%, and 12% of multi-desk requests
have a clash between desks that Munjiz catches before submission. At Expo scale (197 participating countries, the
organisers' public figure) that is tens of thousands of participant hours saved. It serves the participating
countries directly and gives organisers one view of participant services. Growth path: digital ID (challenge 5.2), memory across visits (5.6), more
desks, voice and WhatsApp, demand forecasting.

## Two sides: who sees what

| Role | Signs in with | Sees | Can do |
|---|---|---|---|
| Participant (pavilion team) | pavilion code, e.g. `FRA-2030` | Participant app: its own pavilion's tickets only | Ask, answer, accept a fix, confirm, fix a returned part |
| Desk staff | `logistics.officer`, `security.officer`, `facilities.officer` | Desk console: its own desk's parts only | Approve, request a change, reject with a reason |
| Supervisor | `ops.supervisor` | SLA & escalations, desk console (all desks), ticket tracker | Reassign, decide on a desk's behalf (logged as override) |
| Organiser | `expo.organiser` | Dashboard, ticket tracker with event logs, desk rules | Change rule numbers or switch rules off (logged) |

Demo accounts: every staff PIN is `2030`; the sign-in page also has one-click demo buttons. A pilot would use the
Expo's single sign-on or the digital ID from challenge 5.2. Open the participant in one browser window and Expo
Admin in another; each window keeps its own sign-in, and a refresh keeps you signed in.

## Run

```bash
pip install -r requirements.txt
scripts/n8n_setup.sh             # first time only: .env + token, start n8n in Docker, import and activate workflows
scripts/start.sh                 # n8n + Munjiz API (:8000) + app (:8501)
```

Without Docker, `streamlit run app.py` alone still runs the whole demo; the n8n integration simply stays off
(leave `N8N_WEBHOOK_URL` empty in `.env`).

Sign in as a participant (e.g. **France**) in one window and as **Accreditation** desk staff in another; decisions show up live.

Terminal version of Scenario A:

```bash
python cli.py --demo       # English
python cli.py --demo-ar    # Arabic
python cli.py              # type your own
```

Tests: `python -m pytest -q` (59 tests: Scenario A, roles, the send-back and fix loop, cross-desk clashes, SLA,
organiser rule changes, and the n8n event and API contract)

## How it works

| Step | Where |
|---|---|
| Extract the request into structured fields | `munjiz/extract_local.py` (offline, default) or `munjiz/extract_claude.py` (one tool per desk) |
| Split into desk sub-requests; shared facts (time, pavilion) said once and copied to every desk | `munjiz/agent.py` → `split()` |
| Check each desk's rules: required fields, notice period, time windows, limits, ID formats | `rules/*.yaml` + `munjiz/rules.py` |
| Check clashes between desks (night truck vs crew hours, permits vs truck time) and suggest a fix | `rules/cross_desk.yaml` + `munjiz/conflicts.py` |
| Ask once for what's missing, or show the summary | `munjiz/agent.py` → `compose_reply()` |
| One ticket, sub-requests, decisions (approve / request change / reject), event log | `munjiz/tickets.py`, `munjiz/db.py` (SQLite) |
| A desk sends one part back; the participant fixes only that part (version 2, same ticket) | `munjiz/agent.py` → `run_fix()`, `tickets.resubmit()` |
| Response targets: one reminder, then escalation to the supervisor; reassign and override | `munjiz/tickets.py` → `sla_sweep()`, `sla:` in `rules/*.yaml` |
| Roles and sign-in (participant, desk staff, supervisor, organiser) | `munjiz/users.py`, `views/signin.py` |
| Organiser rule changes without code (stored as overrides, logged) | `munjiz/rules.py` → `set_rule()`, `views/rules_admin.py` |
| Simulated before/after data | `munjiz/simulate.py` (assumptions at the top) |
| UI: sign-in, participant app, desk console, supervisor, tracker, dashboard, desk rules | `app.py`, `views/` |

The LLM only extracts. Rules, follow-up questions and summaries are produced by code, so a bad model
output can't skip a rule, and the human approval step is always there.

## n8n integration

n8n is the integration layer between Munjiz and each desk's own systems. Munjiz never calls desk systems
directly: it sends one event per change, and n8n routes it. Swapping a mock desk for a real system is an n8n
change, not a Munjiz change.

```
Participant app ──► Munjiz (agent + rules + one ticket) ──event──► n8n ──► Logistics system  (gate booking)
                         ▲                                           ├──► Accreditation system
                         │                                           ├──► Utilities work orders
                         └──── decisions ◄── n8n desk-decision ◄─────┴──► desk alerts · participant updates
```

| Workflow (in `n8n/workflows/`) | Trigger | What it does |
|---|---|---|
| Munjiz · Route ticket to desks | webhook `munjiz-events` | `ticket_submitted` and `sub_resubmitted` (a fixed part): one item per desk part → each desk's system (returns its ref, e.g. GATE-1001) → desk alert. `sub_decided` / `ticket_completed`: participant update in their language (including "fix this part"). `sla_reminder` / `sla_escalated`: alert to the desk or the supervisor |
| Munjiz · SLA watchdog | every 5 min | runs the SLA sweep in Munjiz (`POST /api/sla/sweep`); each overdue part gets one reminder, then one escalation, which come back through the first workflow |
| Munjiz · Desk decision intake | webhook `desk-decision` | a desk approves, requests a change or rejects from its own tools (Slack button, email link, its system) → Munjiz decision API |

- Events: `ticket_submitted`, `sub_decided`, `sub_resubmitted`, `ticket_completed`, `sla_reminder`, `sla_escalated` (`munjiz/events.py`). Delivery is logged on the
  ticket (`n8n_sent` / `n8n_failed`); if n8n is down the app carries on.
- API for n8n (`munjiz/api.py`, port 8000): `GET /health` (open), `GET /api/tickets`, `GET /api/tickets/{id}`,
  `GET /api/subrequests/pending?older_than_minutes=30`, `POST /api/subrequests/{id}/decision`
  (`{"decision": "approve" | "request_change" | "reject", "staff": ..., "reason": ...}`; `{"approve": true}` still works),
  `POST /api/sla/sweep`, `POST /mock/desks/{desk}/inbox`. Write calls and ticket reads (worker names and IDs) need
  `X-Munjiz-Token` (generated into `.env`).
- Notification steps are No-op placeholders labelled "Connect Slack, Teams or email here" / "Connect Expo
  app push or WhatsApp here": add credentials in n8n to make them real.
- Edit the workflows in `n8n/make_workflows.py` and re-run `scripts/n8n_setup.sh`, or edit them in the n8n
  editor at http://localhost:5678 (create the owner account on first visit).

Try a desk approving through n8n:

```bash
curl -X POST localhost:5678/webhook/desk-decision -H 'Content-Type: application/json' -d '{"sub_id":"LOG-1001","decision":"approve","staff":"logistics.officer"}'
```

## Expo 2030 Riyadh context

- `munjiz/expo.py`: event dates, phases (build-up, open to visitors, dismantling), participants and sources.
- **Participants:** official participants (countries, international organisations) and non-official participants
  (companies). The countries in the sign-in list have publicly confirmed or signed participation; the others are
  placeholders.
- **Desks:** Logistics & Site Access, Accreditation & Security, Facilities & Utilities. Their rules, gates and
  plots are **simulated**, modelled on how World Expos usually run participant services. Replace them with
  Expo 2030 Riyadh's Special Regulations and site plan when available.
- **Phase-aware rules:** while the Expo is open to visitors, heavy trucks enter only 22:00–06:00; during build-up
  they can come at any time.
- **Expo clock:** the demo moves today's real time of day to Expo day 48 (Sun 17 Nov 2030), so "tomorrow" is a
  day of the Expo. `MUNJIZ_CLOCK=real` uses today's date; `MUNJIZ_EXPO_DATE=2030-06-01` puts the demo in build-up.
- **In-app feature:** the participant page shows Munjiz inside a phone mock-up of the Expo 2030 Riyadh app
  (Home → Munjiz → My requests), next to other app features it doesn't build. Presenter controls sit beside
  the phone. The staff console and dashboard are back-office web screens. The phone is a concept mock-up, not
  the official app, and uses no official logo.
- **Dashboard:** an "At Expo 2030 Riyadh scale" section projects the savings to 197 participants. Only the
  participant count is a public figure; the other inputs are assumptions you can change on screen.

The app says on every page that it is a hackathon prototype and not an official Expo service.

## Agent backends

- **Offline parser** (default, `MUNJIZ_BACKEND=local`): free and deterministic. It covers the demo
  scenarios, not every way of phrasing a request.
- **Claude** (`MUNJIZ_BACKEND=claude`, or pick it in the sidebar): needs `ANTHROPIC_API_KEY`. Uses
  `claude-sonnet-5-5` (Sonnet 5.5) with server-side refusal fallback enabled. Each response is cached in `data/llm_cache/`
  by transcript, so a rehearsed demo replays with no API call. If the call fails on stage, the app falls back
  to the offline parser.

## Demo scripts

In **Presenter controls → Demo scripts** next to the phone:

1. Scenario A (English or Arabic) → follow-up question for plate, workers' IDs and kW
2. Follow-up answer → summary with gate, route, permit and power connection → Confirm
3. Rule demo: a heavy truck at 3 pm is blocked (while the Expo is open, heavy vehicles only 22:00–06:00)
4. Clash demo: a truck at 2 am with power for the screens. Every desk passes on its own, but the utility crews
   only connect power 06:00–23:00. Munjiz suggests connecting the power at 22:00 the evening before; one tap applies it
5. Send-back demo: as Accreditation desk staff, "Send back to the participant" → "John Smith's ID could not be
   verified" → Request a change. The participant's ticket shows Partially approved; tap **Fix: new passport**, then
   send the fix. Only the security part (SEC-…) goes back, as version 2. If two parts came back and only one is
   fixed, only that one goes back and Munjiz says which part still waits for a fix
6. SLA demo: leave a ticket pending (e.g. the clash demo after Apply + Confirm), then as the supervisor open
   Presenter control · SLA demo → ⏩ +300 min: Logistics and Facilities parts escalate, Security gets a reminder

Reset demo tickets from **Ticket tracker → Reset demo** (the simulated history stays; ticket numbers keep counting
and are never reused).

## Simulated data

The dashboard data is synthetic and labelled as such. Every number comes from `ASSUMPTIONS` in
`munjiz/simulate.py`. Replace them with figures from the organisers or mentors.
