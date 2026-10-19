"""Sign in: the participant side (pavilion code) or the Expo Admin side (staff account + PIN)."""
import streamlit as st

from munjiz import users
from munjiz.agent import desk_title
from views.common import icon

ADMIN_HINT = {
    users.DESK_STAFF: "Sees only their desk's parts, already checked. Approves, requests a change or rejects.",
    users.SUPERVISOR: "Sees SLA reminders and escalations across desks. Reassigns or decides on a desk's behalf.",
    users.ORGANISER: "Sees the dashboard, every ticket's event log, and changes desk rules without code.",
}


def enter(user: dict | None):
    if user is None:
        st.error("That code didn't match. Check the demo accounts below.")
        return
    st.session_state.clear()
    st.session_state.user = user
    st.rerun()


def door(icon_name: str, title: str, text: str):
    st.markdown(f'<div class="door-hd"><div class="door-ic">{icon(icon_name)}</div><div><div class="door-t">{title}</div>'
                f'<div class="door-p">{text}</div></div></div>', unsafe_allow_html=True)


signin = st.container(key="signin")
with signin:
    st.markdown(f'<div class="signin-hd"><div class="mark">{icon("check", "i", 2.5)}</div><h1>Sign in to Munjiz</h1>'
                '<p>Two sides, one ticket between them. Pavilion teams ask; Expo Admin staff decide. '
                'Each side only sees what it needs.</p></div>', unsafe_allow_html=True)

    left, right = st.columns(2, gap="medium")

with left:
    with st.container(border=True, key="card_door_participant"):
        door("smartphone", "Participant", "Pavilion teams and their contractors. Sign in with your pavilion code.")
        with st.form("participant_form", border=False):
            code = st.text_input("Pavilion code", placeholder="e.g. FRA-2030")
            if st.form_submit_button("Sign in as participant", type="primary", width="stretch"):
                enter(users.sign_in_with_pavilion_code(code))
        st.markdown('<div class="demo-hint">Demo accounts (prototype)</div>', unsafe_allow_html=True)
        with st.container(horizontal=True, key="quick_participant"):
            for pavilion, pcode in users.PAVILION_CODES.items():
                if st.button(pavilion.replace(" (example)", "").replace(" Pavilion", ""), key=f"q_{pcode}"):
                    enter(users.sign_in_with_pavilion_code(pcode))

with right:
    with st.container(border=True, key="card_door_admin"):
        door("building", "Expo Admin", "Desk staff, supervisors and organisers. Sign in with your account and PIN.")
        staff = [u for u in users.all_users() if u["role"] != users.PARTICIPANT]

        def label(uid: str) -> str:
            u = next(x for x in staff if x["id"] == uid)
            where = desk_title(u["desk"], "en") if u["desk"] else users.ROLE_LABEL[u["role"]].split(" · ")[1].title()
            return f"{u['name']} · {where}"

        with st.form("admin_form", border=False):
            uid = st.selectbox("Account", [u["id"] for u in staff], format_func=label)
            pin = st.text_input("PIN", type="password")
            if st.form_submit_button("Sign in to Expo Admin", type="primary", width="stretch"):
                enter(users.sign_in(uid, pin))
        st.markdown('<div class="demo-hint">Demo accounts (prototype)</div>', unsafe_allow_html=True)
        with st.container(horizontal=True, key="quick_admin"):
            for uid in ("logistics.officer", "security.officer", "facilities.officer", "ops.supervisor", "expo.organiser"):
                u = next(x for x in staff if x["id"] == uid)
                short = desk_title(u["desk"], "en").split(" &")[0] if u["desk"] else u["role"].title()
                if st.button(short, key=f"q_{uid}", help=ADMIN_HINT[u["role"]]):
                    enter(users.sign_in(uid, users.STAFF_PIN))

with signin, st.expander("Demo accounts (prototype) · codes and PINs"):
    st.markdown(
        "**Participants** sign in with their pavilion code: "
        + " · ".join(f"`{c}` {p.replace(' (example)', '')}" for p, c in users.PAVILION_CODES.items())
        + f"\n\n**Expo Admin** accounts all use the demo PIN `{users.STAFF_PIN}`: "
        + " · ".join(f"`{u['id']}`" for u in users.all_users() if u["role"] != users.PARTICIPANT)
        + "\n\nThese are prototype accounts. A pilot would use the Expo's single sign-on, or the digital ID "
          "from challenge 5.2.")
    st.caption("Tip for the demo: open the participant in one browser window and Expo Admin in another. "
               "Each window keeps its own sign-in.")
