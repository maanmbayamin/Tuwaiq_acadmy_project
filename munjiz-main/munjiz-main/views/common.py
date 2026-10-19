import html
import re
from datetime import datetime

import streamlit as st

from munjiz import config, expo
from munjiz.agent import AgentResult, desk_title, describe, locked_text, pick
from munjiz.i18n import fmt_dt
from munjiz.rules import DeskCheck, load_cross_desk, load_rules, rule_count  # noqa: F401

# shadcn/ui, "zinc" dark. One accent (emerald) for state only; amber and red as small badges.
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500&family=IBM+Plex+Sans+Arabic:wght@400;500;600&display=swap');
:root {
  --background: #09090B; --card: #09090B; --muted: #18181B; --accent: #27272A; --border: #27272A; --input: #27272A;
  --foreground: #FAFAFA; --muted-foreground: #A1A1AA; --ring: #D4D4D8;
  --emerald: #10B981; --emerald-fg: #34D399; --amber: #F59E0B; --amber-fg: #FBBF24; --red: #EF4444; --red-fg: #F87171;
  --font: Geist, 'IBM Plex Sans Arabic', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --mono: 'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
  --ar: 'IBM Plex Sans Arabic', Geist, 'Geeza Pro', 'Segoe UI', sans-serif;
}

/* ---- Base --------------------------------------------------------------------------------------- */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stBottomBlockContainer"] {
  background: var(--background) !important; }
html, body, .stApp { font-family: var(--font); -webkit-font-smoothing: antialiased; color: var(--foreground); }
header[data-testid="stHeader"] { background: transparent !important; height: 0 !important; min-height: 0 !important; }
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] { display: none !important; }
.block-container, [data-testid="stMainBlockContainer"] { max-width: 1200px !important; padding: 20px 32px 48px !important; }
.stApp p, .stApp li { color: var(--foreground); font-size: 14px; line-height: 1.6; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4 { font-family: var(--font) !important; color: var(--foreground) !important;
  font-weight: 600 !important; letter-spacing: -0.025em; }
[data-testid="stHeading"] h3 { font-size: 20px !important; line-height: 28px !important; padding: 8px 0 0 !important; }
[data-testid="stHeading"] h4 { font-size: 16px !important; padding: 4px 0 0 !important; }
[data-testid="stHeaderActionElements"] { display: none !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--muted-foreground) !important; font-size: 13px !important; }
.rtl, .rtl * { direction: rtl; text-align: right; font-family: var(--ar); }
a { color: var(--foreground); text-underline-offset: 4px; }
b, strong { font-weight: 600; }
code { font-family: var(--mono) !important; font-size: 12.5px !important; color: var(--foreground) !important;
  background: var(--muted) !important; border: 1px solid var(--border); border-radius: 4px !important; padding: 1px 5px !important; }
hr { border-color: var(--border) !important; }
svg.i { width: 16px; height: 16px; flex: 0 0 auto; vertical-align: -3px; }
svg.i.sm { width: 14px; height: 14px; vertical-align: -2px; }
.muted { color: var(--muted-foreground); }
[data-testid="stSidebar"] { background: var(--background) !important; border-right: 1px solid var(--border); }

/* ---- App bar ----------------------------------------------------------------------------------- */
.st-key-appbar { border-bottom: 1px solid var(--border); margin-bottom: 12px; padding-bottom: 0; gap: 6px !important; }
.st-key-tb_row { min-height: 44px; }
.st-key-tb_right { gap: 12px !important; }
.st-key-tb_row > [data-testid="stLayoutWrapper"]:last-child { margin-left: auto; }
.brand { display: flex; align-items: center; gap: 10px; }
.brand .mark { width: 28px; height: 28px; border-radius: 6px; background: var(--foreground); color: var(--background);
  display: grid; place-items: center; flex: 0 0 28px; }
.brand .mark svg { width: 16px; height: 16px; }
.brand .name { font-size: 15px; font-weight: 600; letter-spacing: -0.01em; line-height: 20px; color: var(--foreground); }
.brand .name .ar { font-family: var(--ar); font-weight: 500; color: var(--muted-foreground); margin-left: 4px; }
.brand .sub { font-size: 12px; color: var(--muted-foreground); line-height: 16px; }
.brand .sep { width: 1px; height: 20px; background: var(--border); margin: 0 4px; }
.who { display: flex; align-items: center; gap: 8px; font-size: 14px; color: var(--foreground); white-space: nowrap; }
.who .avatar { width: 28px; height: 28px; border-radius: 50%; background: var(--accent); color: var(--foreground);
  display: grid; place-items: center; font-size: 11px; font-weight: 600; letter-spacing: 0; }
.who .nm { font-weight: 500; }
.who .sep { width: 1px; height: 20px; background: var(--border); margin-right: 4px; }
.st-key-sign_out button { min-height: 32px !important; height: 32px; padding: 0 12px !important; }
.st-key-sign_out button p { font-size: 13px !important; }
.st-key-topnav { gap: 4px !important; margin-left: -10px; }
.st-key-topnav [data-testid="stPageLink"] a, .st-key-topnav [data-testid="stPageLink-NavLink"] {
  background: transparent !important; border-radius: 6px !important; padding: 6px 10px !important; margin: 0 0 6px !important; }
.st-key-topnav [data-testid="stPageLink-NavLink"]:hover { background: var(--accent) !important; }
.st-key-topnav [data-testid="stPageLink-NavLink"] p, .st-key-topnav [data-testid="stPageLink-NavLink"] span {
  color: var(--muted-foreground) !important; font-size: 14px !important; font-weight: 500 !important; }
.st-key-topnav [data-testid="stPageLink-NavLink"] [data-testid="stIconMaterial"] { font-size: 16px !important; }
.st-key-topnav [class*="st-key-nav_on_"] { position: relative; }
.st-key-topnav [class*="st-key-nav_on_"]::after { content: ""; position: absolute; left: 10px; right: 10px; bottom: -1px; height: 2px;
  background: var(--foreground); border-radius: 1px; }
.st-key-topnav [class*="st-key-nav_on_"] [data-testid="stPageLink-NavLink"] p,
.st-key-topnav [class*="st-key-nav_on_"] [data-testid="stPageLink-NavLink"] span { color: var(--foreground) !important; }

/* ---- Badge ------------------------------------------------------------------------------------- */
.badge, .pill { display: inline-flex; align-items: center; gap: 4px; padding: 2px 10px; border-radius: 6px; font-size: 12px;
  font-weight: 600; line-height: 18px; white-space: nowrap; border: 1px solid transparent; vertical-align: middle; font-family: var(--font); }
.badge.default { background: var(--foreground); color: #18181B; }
.badge.secondary, .pill.in_review, .pill.sla-on_time { background: var(--accent); color: var(--foreground); }
.badge.outline { border-color: var(--border); color: var(--foreground); }
.badge.outline.mutedtext { color: var(--muted-foreground); }
.pill.approved, .pill.completed, .badge.ok { background: rgba(16,185,129,0.15); color: var(--emerald-fg); }
.pill.pending, .pill.changes_requested, .pill.partially_approved, .pill.sla-overdue, .badge.warn {
  background: rgba(245,158,11,0.15); color: var(--amber-fg); }
.pill.rejected, .pill.action_needed, .pill.sla-escalate, .badge.bad { background: rgba(239,68,68,0.15); color: var(--red-fg); }
.badge svg, .pill svg { width: 12px; height: 12px; }
.dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--emerald); flex: 0 0 6px; }

/* ---- Buttons ----------------------------------------------------------------------------------- */
.stButton button, [data-testid="stFormSubmitButton"] button, [data-testid="stPopover"] button, [data-testid="stPopoverButton"] {
  min-height: 36px !important; padding: 0 16px !important; border-radius: 6px !important; box-shadow: none !important;
  transition: background-color .15s, border-color .15s, color .15s !important; }
.stButton button p, [data-testid="stFormSubmitButton"] button p, [data-testid="stPopoverButton"] p {
  font-size: 14px !important; font-weight: 500 !important; }
[data-testid^="stBaseButton-primary"] { background: var(--foreground) !important; color: #18181B !important;
  border: 1px solid var(--foreground) !important; }
[data-testid^="stBaseButton-primary"] p, [data-testid^="stBaseButton-primary"] span { color: #18181B !important; }
[data-testid^="stBaseButton-primary"]:hover:not(:disabled) { background: rgba(250,250,250,0.9) !important; }
[data-testid^="stBaseButton-secondary"], [data-testid="stPopoverButton"] { background: transparent !important;
  border: 1px solid var(--input) !important; color: var(--foreground) !important; }
[data-testid^="stBaseButton-secondary"] p, [data-testid="stPopoverButton"] p { color: var(--foreground) !important; }
[data-testid^="stBaseButton-secondary"]:hover:not(:disabled), [data-testid="stPopoverButton"]:hover { background: var(--accent) !important;
  border-color: var(--input) !important; }
.stButton button:disabled, [data-testid="stFormSubmitButton"] button:disabled { opacity: 0.5 !important; }
.stButton button:focus-visible, [data-testid="stFormSubmitButton"] button:focus-visible, [data-testid="stPopoverButton"]:focus-visible {
  outline: none !important; box-shadow: 0 0 0 2px var(--background), 0 0 0 4px var(--ring) !important; }

/* ---- Inputs ------------------------------------------------------------------------------------ */
[data-testid="stWidgetLabel"] p { font-size: 14px !important; font-weight: 500 !important; color: var(--foreground) !important; }
[data-testid="stTextInputRootElement"], [data-testid="stNumberInputContainer"], .react-aria-ComboBox [role="group"],
[data-testid="stSelectbox"] [data-baseweb="select"] > div, [data-testid="stTextArea"] textarea, [data-baseweb="input"] {
  background: transparent !important; border: 1px solid var(--input) !important; border-radius: 6px !important;
  min-height: 36px; box-shadow: none !important; }
[data-testid="stTextInputRootElement"] input, [data-testid="stNumberInputContainer"] input, .react-aria-ComboBox input {
  background: transparent !important; font-size: 14px !important; color: var(--foreground) !important; }
[data-testid="stTextInputRootElement"]:focus-within, [data-testid="stNumberInputContainer"]:focus-within,
.react-aria-ComboBox [role="group"]:focus-within, [data-testid="stTextArea"] textarea:focus {
  border-color: var(--input) !important; box-shadow: 0 0 0 2px var(--background), 0 0 0 4px var(--ring) !important; }
[data-testid="stNumberInputContainer"] button { background: transparent !important; border-left: 1px solid var(--input) !important; }
[data-testid="stNumberInputContainer"] button:hover { background: var(--accent) !important; }
input::placeholder { color: var(--muted-foreground) !important; opacity: 1; }

/* ---- Card (bordered containers), metric, expander, popover, alert, tabs, segmented control ------- */
[class*="st-key-card"] { border: 1px solid var(--border) !important; border-radius: 12px !important; background: var(--card) !important;
  padding: 24px !important; box-shadow: none !important; }
[class*="st-key-card_q_"], [class*="st-key-card_sv_"] { padding: 20px 24px !important; }
[data-testid="stMetric"] { border: 1px solid var(--border); border-radius: 12px; padding: 20px 24px; background: var(--card); }
[data-testid="stMetricLabel"] p { color: var(--muted-foreground) !important; font-size: 14px !important; font-weight: 500 !important; }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] p { font-size: 28px !important; line-height: 36px !important;
  font-weight: 600 !important; letter-spacing: -0.025em; color: var(--foreground) !important; font-variant-numeric: tabular-nums; }
[data-testid="stTabs"] .react-aria-SelectionIndicator { display: none !important; }
[data-testid="stCheckbox"]:has([role="switch"]) label > div:not([data-testid]) { background: var(--accent) !important; }
[data-testid="stCheckbox"]:has([role="switch"]) label[data-selected="true"] > div:not([data-testid]) { background: var(--foreground) !important; }
[data-testid="stCheckbox"]:has([role="switch"]) label > div:not([data-testid]) > div { background: var(--background) !important;
  box-shadow: none !important; }
[data-testid="stCheckbox"]:has([role="switch"]) label:not([data-selected="true"]) > div:not([data-testid]) > div { background: var(--foreground) !important; }
[data-testid="stExpander"] details { border: 1px solid var(--border) !important; border-radius: 8px !important; background: transparent !important; }
[data-testid="stExpander"] summary { background: transparent !important; padding: 10px 16px !important; }
[data-testid="stExpander"] summary:hover p { text-decoration: underline; text-underline-offset: 4px; }
[data-testid="stExpander"] summary p { font-size: 14px !important; font-weight: 500 !important; color: var(--foreground) !important; }
[data-testid="stExpander"] summary [data-testid="stIconMaterial"] { color: var(--muted-foreground) !important; }
[data-testid="stPopoverBody"], [data-baseweb="popover"] > div { background: var(--background) !important; border: 1px solid var(--border) !important;
  border-radius: 8px !important; box-shadow: 0 1px 2px rgba(0,0,0,0.3) !important; }
[data-testid="stAlertContainer"] { background: transparent !important; border: 1px solid var(--border) !important; border-radius: 8px !important;
  color: var(--foreground) !important; padding: 12px 16px !important; }
[data-testid="stAlertContainer"] p { color: var(--foreground) !important; }
[data-testid="stAlertContentError"] [data-testid="stIconMaterial"], [data-testid="stAlertContentError"] p { color: var(--red-fg) !important; }
[data-testid="stAlertContentWarning"] [data-testid="stIconMaterial"] { color: var(--amber-fg) !important; }
[data-testid="stAlertContentInfo"] [data-testid="stIconMaterial"] { color: var(--muted-foreground) !important; }
[data-testid="stAlertContentSuccess"] [data-testid="stIconMaterial"] { color: var(--emerald-fg) !important; }
[data-testid="stToast"] { background: var(--background) !important; border: 1px solid var(--border) !important; border-radius: 8px !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important; }
[data-testid="stToast"] p { font-size: 13px !important; }
[data-testid="stDataFrame"], [data-testid="stTable"] { border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
[data-baseweb="tab-list"], [data-testid="stTabs"] [role="tablist"] { background: var(--muted) !important; border-radius: 8px; padding: 4px !important;
  gap: 2px !important; width: fit-content; max-width: 100%; }
[data-baseweb="tab"], [data-testid="stTabs"] [role="tab"] { background: transparent !important; border: 1px solid transparent !important;
  border-radius: 6px !important; padding: 4px 12px !important; height: 30px !important; margin: 0 !important; }
[data-baseweb="tab"] p, [data-testid="stTabs"] [role="tab"] p { font-size: 14px !important; font-weight: 500 !important; color: var(--muted-foreground) !important; }
[data-baseweb="tab"][aria-selected="true"], [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  background: var(--background) !important; border-color: var(--border) !important; }
[data-baseweb="tab"][aria-selected="true"] p, [data-testid="stTabs"] [role="tab"][aria-selected="true"] p { color: var(--foreground) !important; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none !important; }
[data-testid="stButtonGroup"] > div { background: var(--muted); border-radius: 8px; padding: 4px; gap: 2px; width: fit-content; }
[data-testid="stButtonGroup"] button { min-height: 30px !important; height: 30px; border: 1px solid transparent !important;
  background: transparent !important; border-radius: 6px !important; padding: 0 12px !important; box-shadow: none !important; }
[data-testid="stButtonGroup"] button p { color: var(--muted-foreground) !important; font-size: 14px !important; font-weight: 500 !important; }
[data-testid="stButtonGroup"] button[data-testid$="Active"], [data-testid="stButtonGroup"] button[aria-checked="true"] {
  background: var(--background) !important; border-color: var(--border) !important; }
[data-testid="stButtonGroup"] button[data-testid$="Active"] p, [data-testid="stButtonGroup"] button[aria-checked="true"] p {
  color: var(--foreground) !important; }

/* ---- Page header ------------------------------------------------------------------------------- */
.ph { margin: 12px 0 20px; }
.ph .crumb { font-size: 14px; color: var(--muted-foreground); display: flex; align-items: center; gap: 6px; }
.ph .crumb svg { width: 14px; height: 14px; }
.ph h1 { font-size: 30px !important; line-height: 36px !important; font-weight: 600 !important; letter-spacing: -0.025em !important;
  margin: 6px 0 0 !important; padding: 0 !important; }
.ph p { color: var(--muted-foreground) !important; margin: 6px 0 0; max-width: 72ch; }

/* ---- HTML card + alert ------------------------------------------------------------------------- */
.card { border: 1px solid var(--border); border-radius: 12px; background: var(--card); }
.card .hd { padding: 24px 24px 0; display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.card .ct { font-size: 16px; font-weight: 600; letter-spacing: -0.01em; line-height: 1.2; color: var(--foreground); }
.card .cd { font-size: 14px; color: var(--muted-foreground); margin-top: 6px; }
.card .bd { padding: 20px 24px 24px; }
.alert { display: flex; gap: 12px; border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; margin: 4px 0 16px; }
.alert svg { width: 16px; height: 16px; margin-top: 3px; color: var(--foreground); flex: 0 0 16px; }
.alert .at { font-size: 14px; font-weight: 500; color: var(--foreground); line-height: 22px; }
.alert .ad { font-size: 14px; color: var(--muted-foreground); line-height: 20px; }
.line { display: flex; align-items: center; gap: 8px; font-size: 14px; color: var(--foreground); margin: 2px 0; }
.line svg { width: 16px; height: 16px; color: var(--muted-foreground); }
.line.ok svg { color: var(--emerald-fg); }
.line .muted { color: var(--muted-foreground); }
.conflict-box { border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px; margin: 6px 0; font-size: 14px; }

/* ---- KPI cards --------------------------------------------------------------------------------- */
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 0 0 16px; }
.kpi { border: 1px solid var(--border); border-radius: 12px; padding: 20px 24px; background: var(--card); }
.kpi .l { font-size: 14px; font-weight: 500; color: var(--muted-foreground); line-height: 20px; }
.kpi .v { font-size: 30px; font-weight: 600; line-height: 36px; margin-top: 8px; letter-spacing: -0.025em; color: var(--foreground);
  font-variant-numeric: tabular-nums; }
.kpi .row { display: flex; align-items: center; gap: 8px; margin-top: 6px; flex-wrap: wrap; }
.kpi .w { font-size: 13px; color: var(--muted-foreground); }

/* ---- Participant: heading, agent trace, demo scripts ------------------------------------------- */
.lead { margin: 4px 0 20px; }
.lead .tag { display: inline-flex; }
.lead h2 { font-size: 30px !important; line-height: 36px !important; font-weight: 600 !important; letter-spacing: -0.025em !important;
  margin: 12px 0 0 !important; padding: 0 !important; }
.lead .ar { font-family: var(--ar); font-size: 15px; color: var(--muted-foreground); direction: rtl; text-align: left; margin-top: 4px; }
.lead p { color: var(--muted-foreground) !important; margin: 10px 0 0; max-width: 62ch; }
.steps { position: relative; }
.step { display: grid; grid-template-columns: 20px 1fr; gap: 12px; padding-bottom: 16px; position: relative; }
.step:last-child { padding-bottom: 0; }
.step:not(:last-child)::before { content: ""; position: absolute; left: 9.5px; top: 24px; bottom: 4px; width: 1px; background: var(--border); }
.step .ic { width: 20px; height: 20px; display: grid; place-items: center; color: #52525B; }
.step .ic svg { width: 20px; height: 20px; }
.step.done .ic { color: var(--emerald-fg); }
.step.active .ic .dot { width: 8px; height: 8px; flex-basis: 8px; }
.step .t { font-size: 14px; font-weight: 500; color: var(--foreground); line-height: 20px; }
.step.pending .t { color: var(--muted-foreground); font-weight: 400; }
.step .d { font-size: 13px; color: var(--muted-foreground); line-height: 18px; margin-top: 2px; }
.step .chips { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; }
.step .chips .badge { font-weight: 500; }
.demo-label { font-size: 14px; font-weight: 500; color: var(--foreground); margin: 24px 0 2px; }
.demo-label span { color: var(--muted-foreground); font-weight: 400; }
.st-key-demo { gap: 8px !important; }
.st-key-demo button { min-height: 32px !important; height: 32px; padding: 0 12px !important; }
.st-key-demo button p { font-size: 13px !important; }
iframe[title*="phone"] { background: transparent !important; color-scheme: light; }

/* ---- Desk cards and the small ticket (legacy renderers) ---------------------------------------- */
.desk { border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; margin: 6px 0; }
.desk .hd { display: flex; align-items: center; gap: 8px; font-weight: 500; font-size: 13px; color: var(--foreground); }
.desk .hd .badge { margin-left: auto; }
.rtl .desk .hd .badge { margin-left: 0; margin-right: auto; }
.desk .bd { font-size: 13px; color: var(--muted-foreground); margin-top: 4px; line-height: 1.45; }
.desk .note { font-size: 12px; color: var(--muted-foreground); margin-top: 4px; display: flex; gap: 6px; align-items: center; }
.intro { font-size: 14px; color: var(--foreground); }
.tk { border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-top: 6px; }
.tk .top { display: flex; align-items: center; justify-content: space-between; }
.tk .id { font-weight: 600; font-size: 18px; color: var(--foreground); letter-spacing: -0.01em; }
.tk .lbl { font-size: 12px; color: var(--muted-foreground); }
.tk .bar { display: flex; gap: 4px; margin: 12px 0 8px; }
.tk .bar span { flex: 1; height: 4px; border-radius: 2px; background: var(--accent); }
.tk .bar span.approved { background: var(--emerald); } .tk .bar span.rejected { background: var(--red); }
.tk .bar span.changes_requested { background: var(--amber); }
.tk .row { display: flex; align-items: center; gap: 8px; padding: 8px 0; border-top: 1px solid var(--border); font-size: 13px; }
.tk .row .who { font-size: 12px; color: var(--muted-foreground); }
.tk .row .pill { margin-left: auto; }
.rtl .tk .row .pill { margin-left: 0; margin-right: auto; }
.tk .foot { font-size: 12px; color: var(--muted-foreground); margin-top: 8px; display: flex; gap: 6px; align-items: center; }
.tk .done { margin-top: 10px; border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px; font-size: 13px; display: flex; gap: 8px;
  align-items: center; } .tk .done svg { color: var(--emerald-fg); }
.tkrow { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 10px 0; border-top: 1px solid var(--border); font-size: 14px; }
.tkrow:first-of-type { border-top: none; }
.tkrow .nm { font-weight: 500; display: inline-flex; gap: 8px; align-items: center; }
.tkrow .nm svg { color: var(--muted-foreground); }
.tkrow .meta { color: var(--muted-foreground); font-size: 13px; }
.tkrow .why { flex-basis: 100%; color: var(--muted-foreground); font-size: 13px; padding-left: 24px; }
.cardtitle { display: flex; align-items: center; gap: 10px; font-size: 18px; font-weight: 600; letter-spacing: -0.01em; color: var(--foreground); }

/* ---- Sign-in ----------------------------------------------------------------------------------- */
.st-key-signin { max-width: 880px; margin: 24px auto 0; }
.signin-hd { text-align: center; margin: 8px 0 24px; }
.signin-hd .mark { width: 40px; height: 40px; border-radius: 8px; background: var(--foreground); color: var(--background);
  display: inline-grid; place-items: center; }
.signin-hd .mark svg { width: 22px; height: 22px; }
.signin-hd h1 { font-size: 24px !important; line-height: 32px !important; margin: 16px 0 0 !important; padding: 0 !important; }
.signin-hd p { color: var(--muted-foreground) !important; margin: 6px auto 0; max-width: 56ch; }
.door-hd { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 4px; }
.door-ic { width: 36px; height: 36px; border-radius: 8px; border: 1px solid var(--border); display: grid; place-items: center; flex: 0 0 36px;
  color: var(--foreground); }
.door-ic svg { width: 18px; height: 18px; }
.door-t { font-size: 18px; font-weight: 600; letter-spacing: -0.01em; color: var(--foreground); line-height: 24px; }
.door-p { color: var(--muted-foreground); font-size: 14px; line-height: 20px; margin-top: 2px; }
.demo-hint { font-size: 13px; color: var(--muted-foreground); margin: 4px 0 -4px; padding-top: 16px; border-top: 1px solid var(--border); }
[class*="st-key-door_"] [data-testid="stHorizontalBlock"], [class*="st-key-quick_"] { gap: 8px !important; }
[class*="st-key-quick_"] button { min-height: 32px !important; height: 32px; padding: 0 12px !important; }
[class*="st-key-quick_"] button p { font-size: 13px !important; }

.expo-footer { color: var(--muted-foreground); font-size: 12px; border-top: 1px solid var(--border); margin-top: 40px; padding-top: 16px; line-height: 1.6; }
.expo-footer a { color: var(--muted-foreground); text-decoration: underline; }
</style>
"""

# lucide icons (https://lucide.dev), stroke = currentColor.
_ICON = {
    "truck": '<path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M15 18H9"/><path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14"/><circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/>',
    "id-card": '<path d="M16 10h2"/><path d="M16 14h2"/><path d="M6.17 15a3 3 0 0 1 5.66 0"/><circle cx="9" cy="11" r="2"/><rect x="2" y="5" width="20" height="14" rx="2"/>',
    "zap": '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>',
    "git-merge": '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M6 21V9a9 9 0 0 0 9 9"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "circle-check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "circle": '<circle cx="12" cy="12" r="9"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "shield-check": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    "smartphone": '<rect width="14" height="20" x="5" y="2" rx="2" ry="2"/><path d="M12 18h.01"/>',
    "building": '<rect width="16" height="20" x="4" y="2" rx="2" ry="2"/><path d="M9 22v-4h6v4"/><path d="M8 6h.01"/><path d="M16 6h.01"/><path d="M12 6h.01"/><path d="M12 10h.01"/><path d="M12 14h.01"/><path d="M16 10h.01"/><path d="M16 14h.01"/><path d="M8 10h.01"/><path d="M8 14h.01"/>',
    "trending-down": '<path d="M16 17h6v-6"/><path d="m22 17-8.5-8.5-5 5L2 7"/>',
    "trending-up": '<path d="M16 7h6v6"/><path d="m22 7-8.5 8.5-5-5L2 17"/>',
    "chevron-right": '<path d="m9 18 6-6-6-6"/>',
    "corner-down-right": '<path d="m15 10 5 5-5 5"/><path d="M4 4v7a4 4 0 0 0 4 4h12"/>',
}


def icon(name: str, cls: str = "i", width: float = 2) -> str:
    return (f'<svg class="{cls}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round">{_ICON.get(name, "")}</svg>')


def desk_icon(desk: str, cls: str = "i") -> str:
    """The desk's icon (a lucide name in rules/*.yaml), for HTML only."""
    name = load_cross_desk()["icon"] if desk == "cross_desk" else load_rules()[desk]["icon"]
    return icon(name, cls)


def badge(text: str, variant: str = "outline") -> str:
    return f'<span class="badge {variant}">{text}</span>'


STATUS = {
    "pending": {"en": "Pending", "ar": "قيد المراجعة"},
    "approved": {"en": "Approved", "ar": "تمت الموافقة"},
    "rejected": {"en": "Rejected", "ar": "مرفوض"},
    "in_review": {"en": "In review", "ar": "قيد المراجعة"},
    "completed": {"en": "Done", "ar": "منجز"},
    "action_needed": {"en": "Action needed", "ar": "يحتاج إجراء"},
    "changes_requested": {"en": "Change requested", "ar": "مطلوب تعديل"},
    "partially_approved": {"en": "Partially approved", "ar": "موافقة جزئية"},
}


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def _clock_badge() -> str:
    now = config.now()
    phase = expo.phase(now)
    day = f"Expo day {expo.expo_day(now)} of {expo.DAYS}" if phase == "operations" else expo.PHASE_LABEL[phase]["en"]
    sim = ' <span class="muted">· simulated</span>' if config.CLOCK == "expo" else ""
    return (f'<span class="badge outline" title="Expo 2030 Riyadh · 1 Oct 2030 – 31 Mar 2031" style="font-weight:500">'
            f'{icon("clock", "i sm")}{day} · {now:%a %d %b, %H:%M}{sim}</span>')


def app_bar(pages: list | None = None, current=None):
    """Top bar: Munjiz mark and name, the Expo clock, who is signed in and sign-out; page tabs underneath."""
    from munjiz.users import ROLE_LABEL
    user = st.session_state.get("user")
    side = ("Expo Admin console" if user and user["role"] != "participant" else
            "Participant app" if user else "Participant request agent")
    with st.container(key="appbar"):
        with st.container(key="tb_row", horizontal=True, vertical_alignment="center", gap="small"):
            st.markdown(f'<div class="brand"><div class="mark">{icon("check", "i", 2.5)}</div><div>'
                        f'<div class="name">Munjiz<span class="ar">منجز</span></div>'
                        f'<div class="sub">{side} · Expo 2030 Riyadh · Challenge 5.5</div></div></div>',
                        unsafe_allow_html=True, width="stretch")
            with st.container(key="tb_right", horizontal=True, vertical_alignment="center", width="content"):
                st.markdown(_clock_badge(), unsafe_allow_html=True, width="content")
                if user:
                    role = ROLE_LABEL[user["role"]].split(" · ")[1]
                    name = user["name"]
                    initials = "".join(w[0] for w in name.replace("(example)", "").split()[:2]).upper()
                    st.markdown(f'<div class="who"><span class="sep"></span>'
                                f'<span class="avatar">{html.escape(initials)}</span><span class="nm">{html.escape(name)}</span>'
                                f'{badge(role.capitalize(), "secondary")}</div>', unsafe_allow_html=True, width="content")
                    if st.button("Sign out", key="sign_out"):
                        for k in list(st.session_state.keys()):
                            del st.session_state[k]
                        st.query_params.clear()
                        st.rerun()
        if pages and len(pages) > 1:
            with st.container(key="topnav", horizontal=True, vertical_alignment="bottom", gap=None):
                for p in pages:
                    on = current is not None and p.url_path == current.url_path
                    with st.container(key=f"nav_{'on_' if on else ''}{p.url_path}", width="content"):
                        st.page_link(p)


def expo_header():
    """Kept for callers that only want the bar without page tabs."""
    app_bar()


def expo_footer():
    st.markdown(
        '<div class="expo-footer">Munjiz is a hackathon prototype for Expo 2030 Riyadh challenge 5.5 and is not an '
        'official Expo service; the phone is a concept mock-up of the Expo app. Desk rules, gates, plots and dashboard '
        'data are simulated. Event facts: '
        + " · ".join(f'<a href="{url}" target="_blank">{label}</a>' for label, url in expo.SOURCES)
        + "</div>", unsafe_allow_html=True)


def page_header(eyebrow: str, title: str, sub: str):
    crumbs = f' {icon("chevron-right")} '.join(html.escape(x) for x in eyebrow.split(" · "))
    st.markdown(f'<div class="ph"><div class="crumb">{crumbs}</div><h1>{title}</h1><p>{sub}</p></div>',
                unsafe_allow_html=True)


def alert(title: str, text: str, name: str = "info"):
    """shadcn Alert: bordered, icon, title and muted description."""
    st.markdown(f'<div class="alert">{icon(name)}<div><div class="at">{title}</div><div class="ad">{text}</div></div></div>',
                unsafe_allow_html=True)


def kpi_cards(items: list[dict]):
    """items: {label, value, was?, change?, plain?}"""
    def change(c: str) -> str:
        if len(c) > 14:  # a sentence, not a delta
            return f'<span class="w">{c}</span>'
        trend = "trending-down" if c.startswith(("-", "−")) else "trending-up"
        return badge(icon(trend) + c, "ok")

    cards = "".join(
        f'<div class="kpi"><div class="l">{k["label"]}</div><div class="v">{k["value"]}</div>'
        + ('<div class="row">' + (change(k["change"]) if k.get("change") else "")
           + (f'<span class="w">from {k["was"]} today</span>' if k.get("was") else "") + "</div>"
           if k.get("change") or k.get("was") else "")
        + "</div>" for k in items)
    st.markdown(f'<div class="kpis">{cards}</div>', unsafe_allow_html=True)


def text(md: str, lang: str = "en"):
    if lang == "ar":
        st.markdown(f'<div class="rtl">\n\n{md}\n\n</div>', unsafe_allow_html=True)
    else:
        st.markdown(md)


def pill(status: str, lang: str = "en") -> str:
    return f'<span class="pill {status}">{STATUS[status][lang]}</span>'


def ago(iso: str) -> str:
    secs = int((config.now() - datetime.fromisoformat(iso)).total_seconds())
    return duration(secs) + " ago"


def duration(secs: float, lang: str = "en") -> str:
    secs = max(int(secs), 0)
    s, m, h = ("ث", "د", "س") if lang == "ar" else ("s", "min", "h")
    if secs < 60:
        return f"{secs} {s}"
    if secs < 3600:
        return f"{secs // 60} {m} {secs % 60:02d} {s}"
    return f"{secs // 3600} {h} {secs % 3600 // 60:02d} {m}"


def md_plain(s: str) -> str:
    return s.replace("**", "")


def md_bold(s: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(s, quote=False))


def describe_sub(sub: dict, lang: str = "en") -> str:
    return describe(DeskCheck(desk=sub["desk"], payload=sub["payload"], assigned=sub["assigned"]), lang)


DESK_STATE = {
    "ok": {"en": "Ready", "ar": "جاهز"},
    "missing": {"en": "Needs info", "ar": "ينقصه معلومات"},
    "blocked": {"en": "Rule", "ar": "مخالفة قاعدة"},
    "conflict": {"en": "Clash between desks", "ar": "تعارض بين الجهات"},
}
DESK_BADGE = {"ok": "ok", "missing": "warn", "blocked": "bad", "conflict": "bad"}


def desk_cards(result: AgentResult) -> list[dict]:
    """Snapshot of each desk's sub-request for the chat: state plus what's missing or what will be booked.
    A last card shows clashes between desks (the cross-desk check), with the suggested fix."""
    lang, cards = result.language, []
    for desk, check in result.checks.items():
        count = check.payload.get("worker_count")
        missing = [i.message[lang] + (f" ({count} {'عمال' if lang == 'ar' else 'workers'})"
                                      if i.field == "workers" and count else "")
                   for i in check.blocking if i.kind == "missing"]
        problems = [i.message[lang] for i in check.blocking if i.kind == "rule"]
        state = "blocked" if problems else "missing" if missing else "ok"
        cards.append({"desk": desk, "state": state, "missing": missing, "problems": problems,
                      "notes": [i.message[lang] for i in check.notes],
                      "detail": describe(check, lang) if check.ok else ""})
    for card in cards:
        rules = load_rules()[card["desk"]]
        card.update(icon=rules["icon"], title=rules["title"][lang])
    clashes = result.blocking_conflicts
    if clashes:
        cross = load_cross_desk()
        locked = [locked_text(c, result.locked, lang) for c in clashes]
        cards.append({"desk": "cross_desk", "state": "conflict", "missing": [], "notes": [],
                      "problems": [c.message[lang] for c in clashes] + [md_plain(x) for x in locked if x],
                      "fixes": [c.fix[lang] for c, lock in zip(clashes, locked) if c.fix and not lock],
                      "icon": cross["icon"], "title": cross["title"][lang], "detail": ""})
    for card in cards:
        card.setdefault("fixes", [])
        card["notes"] += [c.message[lang] for c in result.conflicts if not c.blocking and card["desk"] in c.desks]
    return cards


def render_desk_cards(cards: list[dict], lang: str) -> str:
    out = []
    for c in cards:
        if c["state"] == "ok":
            body = md_bold(c["detail"])
        else:
            body = "<br>".join("• " + html.escape(x) for x in c["missing"] + c["problems"])
        notes = "".join(f'<div class="note">{icon("info", "i sm")}{html.escape(n)}</div>' for n in c["notes"])
        notes += "".join(f'<div class="note">{icon("check", "i sm")}{html.escape(f)}</div>' for f in c.get("fixes", []))
        out.append(f'<div class="desk {c["state"]}"><div class="hd">{icon(c["icon"])} {html.escape(c["title"])}'
                   f'{badge(DESK_STATE[c["state"]][lang], DESK_BADGE[c["state"]])}</div><div class="bd">{body}</div>{notes}</div>')
    return "".join(out)


def ticket_mini(ticket: dict, lang: str = "en"):
    """The single ticket as the participant sees it in the app: progress bar, one row per desk, timers."""
    ar = lang == "ar"
    created = datetime.fromisoformat(ticket["created_at"])
    started = datetime.fromisoformat(ticket["started_at"] or ticket["created_at"])
    end = datetime.fromisoformat(ticket["closed_at"]) if ticket["closed_at"] else config.now()
    approved = sum(s["status"] == "approved" for s in ticket["subs"])
    rows = "".join(
        f'<div class="row"><div><b>{desk_title(s["desk"], lang)}</b><div class="who">{s["id"]}'
        + (f' · {s["decided_by"]} · {fmt_dt(s["decided_at"], lang)}' if s["status"] != "pending" else "")
        + (f' · {html.escape(s["reason"])}' if s.get("reason") else "")
        + f'</div></div>{pill(s["status"], lang)}</div>' for s in ticket["subs"])
    bar = "".join(f'<span class="{s["status"]}"></span>' for s in ticket["subs"])
    foot = (icon("clock", "i sm") + f'{duration((created - started).total_seconds(), lang)} '
            + ("حتى الإرسال" if ar else "to submit") + " · "
            + (("أُنجز خلال " if ar else "done in ") if ticket["closed_at"] else ("مفتوحة منذ " if ar else "open "))
            + duration((end - created).total_seconds(), lang)
            + f" · {approved}/{len(ticket['subs'])} " + ("موافقات" if ar else "desks approved"))
    done = ""
    if ticket["status"] == "completed":
        done = (f'<div class="done">{icon("circle-check")}' + ("تمت موافقة جميع الجهات. طلبك منجز." if ar else
                "All desks approved. Your request is done.") + "</div>")
    st.markdown(
        f'<div class="{"rtl" if ar else ""}"><div class="tk"><div class="top"><div>'
        f'<div class="lbl">{"تذكرة واحدة" if ar else "One ticket"}</div><div class="id">{ticket["id"]}</div></div>'
        f'{pill(ticket["status"], lang)}</div><div class="bar">{bar}</div>{rows}<div class="foot">{foot}</div>{done}</div></div>',
        unsafe_allow_html=True)


def ticket_card(ticket: dict, lang: str = "en"):
    """Wide ticket view for the tracker: one row per desk, live status, and the timers."""
    with st.container(border=True, key=f"card_tk_{ticket['id']}"):
        st.markdown(f'<div class="cardtitle">Ticket {ticket["id"]} {pill(ticket["status"], lang)}</div>',
                    unsafe_allow_html=True)
        rows = []
        for sub in ticket["subs"]:
            line = (f'<span class="nm">{desk_icon(sub["desk"])}{desk_title(sub["desk"], lang)}</span>'
                    f'{pill(sub["status"], lang)} <code>{sub["id"]}</code>')
            if (sub.get("version") or 1) > 1:
                line += f' <span class="meta">v{sub["version"]} (fixed by the participant)</span>'
            if sub["status"] != "pending":
                line += f' <span class="meta">{sub["decided_by"]} · {fmt_dt(sub["decided_at"], lang)}</span>'
            if sub.get("reason"):
                line += f'<span class="why">{html.escape(sub["reason"])}</span>'
            rows.append(f'<div class="tkrow">{line}</div>')
        st.markdown(f'<div class="{"rtl" if lang == "ar" else ""}" style="margin:8px 0 16px">{"".join(rows)}</div>',
                    unsafe_allow_html=True)
        created = datetime.fromisoformat(ticket["created_at"])
        started = datetime.fromisoformat(ticket["started_at"] or ticket["created_at"])
        end = datetime.fromisoformat(ticket["closed_at"]) if ticket["closed_at"] else config.now()
        cols = st.columns(3)
        cols[0].metric("Participant time to submit", duration((created - started).total_seconds()))
        cols[1].metric("Done in" if ticket["closed_at"] else "Open for", duration((end - created).total_seconds()))
        approved = sum(s["status"] == "approved" for s in ticket["subs"])
        cols[2].metric("Desks approved", f"{approved} / {len(ticket['subs'])}")


def sla_pill(info: dict) -> str:
    label = {"on_time": f"{info['waited_minutes']:.0f} of {info['review_minutes']} min",
             "overdue": f"Overdue · {info['waited_minutes']:.0f} min (target {info['review_minutes']})",
             "escalate": f"Escalated · {info['waited_minutes']:.0f} min"}[info["level"]]
    mark = icon("clock") if info["level"] == "on_time" else icon("alert")
    return f'<span class="pill sla-{info["level"]}">{mark}{label}</span>'


def user_bar():
    """Signed-in user and sign-out now live in app_bar(); kept so older callers still work."""
    return


__all__ = ["page_header", "kpi_cards", "expo_header", "expo_footer", "inject_css", "text", "pill", "ago", "duration", "describe_sub",
           "ticket_card", "ticket_mini", "desk_cards", "render_desk_cards", "rule_count", "pick", "desk_title",
           "sla_pill", "user_bar", "app_bar", "alert", "icon", "desk_icon", "badge"]
