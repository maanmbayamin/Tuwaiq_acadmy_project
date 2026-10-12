import streamlit as st

from sports import SportService
from diseases import Diseases
from nutrition import nutrition
from Clinic import Clinic

st.set_page_config(page_title="Riyadh Health Cluster", page_icon="🏥", layout="wide")

# same colors and fonts as our presentation
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400..800&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    --ink: #1E1B16; --cream: #F3EDE2; --paper: #FFFDF8; --muted: #6F675B;
    --orange: #E4572E; --green: #14463A; --yellow: #F2C14E; --peach: #F6D7C3; --red: #C2362B;
}
.stApp { background: var(--cream); color: var(--ink); }
.stApp, .stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp button {
    font-family: "Bricolage Grotesque", ui-sans-serif, system-ui, sans-serif;
}
.stApp h1, .stApp h2, .stApp h3 { color: var(--ink); letter-spacing: -.02em; }

/* no sidebar, the menu is on top */
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] { display: none; }
.top-logo { display: flex; align-items: center; gap: 10px; font-weight: 800; font-size: 1.35rem; letter-spacing: -.02em; color: var(--ink); padding-top: 6px; }
.top-logo svg { width: 28px; height: 28px; }
.top-logo svg rect { fill: var(--ink); } .top-logo svg rect.c { fill: var(--orange); }
[data-testid="stButtonGroup"] button {
    background: var(--paper); color: var(--ink); font-weight: 650;
    border: 2px solid var(--ink) !important; border-radius: 11px !important; margin-right: 8px;
    box-shadow: 3px 3px 0 var(--ink);
}
[data-testid="stButtonGroup"] button[aria-checked="true"] { background: var(--orange) !important; color: #FFF6EC; transform: translate(2px,2px); box-shadow: 1px 1px 0 var(--ink); }
[data-testid="stButtonGroup"] button[aria-checked="true"] * { color: #FFF6EC !important; }

/* patient file inputs: the example text shows in grey until the patient types */
.stApp input::placeholder { color: #A39B8F !important; opacity: 1; }
[data-baseweb="select"] [data-baseweb="select"] div[aria-selected="false"], [data-baseweb="select"] div:has(> input[aria-autocomplete]) { color: #A39B8F; }

/* page header like the divider slides: big number + title */
.banner {
    display: flex; align-items: center; gap: 28px;
    border: 2px solid var(--ink); border-radius: 18px; padding: 24px 32px; margin-bottom: 26px;
    box-shadow: 6px 6px 0 var(--ink);
}
.banner .num { font-weight: 800; font-size: 5.5rem; line-height: .8; letter-spacing: -.06em; }
.banner .lab { font: 500 12px/1.3 "IBM Plex Mono", monospace; letter-spacing: .07em; text-transform: uppercase; opacity: .75; }
.banner h1 { font-weight: 800; font-size: 2.6rem; line-height: 1 !important; letter-spacing: -.035em; margin: 6px 0 4px; padding: 0; }
.banner p { margin: 0; font-size: 1.05rem; opacity: .85; }
.banner svg { width: 82px; height: 82px; flex: none; }
.banner.t { background: var(--orange); color: #FFF6EC; }
.banner.t h1 { color: #FFF6EC; } .banner.t svg rect { fill: #FFF6EC; } .banner.t svg rect.c { fill: var(--ink); }
.banner.g { background: var(--green); color: var(--cream); }
.banner.g h1 { color: var(--cream); } .banner.g .num { color: var(--yellow); }
.banner.p { background: var(--peach); color: #2B1B13; }
.banner.p h1 { color: #2B1B13; } .banner.p .num { color: var(--red); }

/* cards with the hard shadow from the slides */
.card {
    background: var(--paper); border: 2px solid var(--ink); border-radius: 16px; padding: 20px 22px;
    box-shadow: 5px 5px 0 var(--ink); height: 100%;
}
.card .lab { font: 500 12px/1.3 "IBM Plex Mono", monospace; letter-spacing: .07em; color: var(--muted); }
.card h3 { margin: 6px 0 6px; padding: 0; font-size: 1.3rem; font-weight: 700; color: var(--ink); border-top: 6px solid var(--c, var(--orange)); padding-top: 12px; }
.card p { color: var(--muted); margin-bottom: 0; }

[data-testid="stMetric"] {
    background: var(--paper); border: 2px solid var(--ink); border-radius: 16px; padding: 14px 20px;
    box-shadow: 5px 5px 0 var(--ink);
}
[data-testid="stMetricLabel"] p { font-family: "IBM Plex Mono", monospace !important; text-transform: uppercase; letter-spacing: .06em; font-size: 12px; color: var(--muted); }
[data-testid="stMetricValue"] { font-weight: 800; letter-spacing: -.03em; }
[data-testid="stMetricValue"] * { white-space: normal !important; overflow: visible !important; text-overflow: clip !important; line-height: 1.15; }

.ticket {
    background: var(--paper); border: 2px dashed var(--ink); border-radius: 16px; padding: 22px;
    box-shadow: 5px 5px 0 var(--ink);
}
.ticket h3 { margin-top: 0; }
.ticket .row { display: flex; justify-content: space-between; padding: 7px 0; border-bottom: 1.5px solid rgba(30,27,22,.14); }
.ticket .row span:first-child { color: var(--muted); font-family: "IBM Plex Mono", monospace; font-size: .9rem; }
.ticket .row span:last-child { font-weight: 700; color: var(--ink); }

.tag { display: inline-block; padding: 3px 12px; border-radius: 999px; font-weight: 700; color: white; border: 2px solid var(--ink); }
.Urgent { background: var(--red); }
.Soon { background: #B7791F; }
.Routine { background: #2F7D4F; }

/* tactile buttons from the slides */
div.stButton > button {
    background: var(--paper); color: var(--ink); font-weight: 650;
    border: 2px solid var(--ink); border-radius: 11px; padding: 8px 22px;
    box-shadow: 3px 3px 0 var(--ink); transition: transform .12s, box-shadow .12s, background .15s;
}
div.stButton > button:hover { background: var(--orange); color: #FFF6EC; border-color: var(--ink); transform: translate(-1px,-1px); box-shadow: 4px 4px 0 var(--ink); }
div.stButton > button:active { transform: translate(3px,3px); box-shadow: 0 0 0 var(--ink); }
</style>
""", unsafe_allow_html=True)


def logo(): # the plus logo from the presentation, made of 5 squares
    squares = ""
    for x, y in [(0, -1), (-1, 0), (0, 0), (1, 0), (0, 1)]:
        center = ' class="c"' if x == 0 and y == 0 else ""
        squares += '<rect x="' + str(x - .46) + '" y="' + str(y - .46) + '" width=".92" height=".92" rx=".2"' + center + '/>'
    return '<svg viewBox="-1.62 -1.62 3.24 3.24">' + squares + '</svg>'


def banner(title, text, number="", label="", color="g"): # the big box on top of every page, like the divider slides
    left = '<div class="num">' + number + '</div>' if number else logo()
    st.markdown('<div class="banner ' + color + '">' + left + '<div><div class="lab">' + label + '</div><h1>' + title + '</h1><p>' + text + '</p></div></div>',
                unsafe_allow_html=True)


def card(title, text, number="", color="#E4572E"): # white box with a title and small text
    st.markdown('<div class="card" style="--c:' + color + '"><div class="lab">' + number + '</div><h3>' + title + '</h3><p>' + text + '</p></div>',
                unsafe_allow_html=True)


# the patient file is kept in session_state so it stays filled when we move between tabs
patient_keys = ["patient_id", "name", "age", "gender", "weight", "height"]
for key in patient_keys:
    if key in st.session_state:
        st.session_state[key] = st.session_state[key] # streamlit forgets inputs of a hidden tab, this keeps them

patient_id = st.session_state.get("patient_id")
name = st.session_state.get("name")
age = st.session_state.get("age")
gender = st.session_state.get("gender")
weight = st.session_state.get("weight")
height = st.session_state.get("height")
file_done = all(st.session_state.get(key) not in (None, "") for key in patient_keys)


def go_to_patient_file(): # used by the button when the file is empty
    st.session_state.page = "Patient file"


def need_patient_file(): # stop the page if the patient did not fill the file yet
    if not file_done:
        card("🗂️ Fill your patient file first", "We need your details to calculate this for you. It takes less than a minute.", "STEP 1", "#E4572E")
        st.write("")
        st.button("Open patient file", on_click=go_to_patient_file)
        st.stop()


# top bar: logo on the left, menu next to it
pages = ["Home", "Patient file", "Diseases", "Nutrition", "Sports", "Clinic"]
if "page" not in st.session_state:
    st.session_state.page = "Home"

logo_col, menu_col = st.columns([1, 3])
logo_col.markdown('<div class="top-logo">' + logo() + 'Riyadh Health Cluster</div>', unsafe_allow_html=True)
with menu_col:
    page = st.segmented_control("Menu", pages, key="page", label_visibility="collapsed")
if page is None: # clicking the open tab again unselects it, so we go home
    page = "Home"
st.write("")


if page == "Home": # home page
    banner("Riyadh Health Cluster", "Welcome " + (name or "Guest") + ", how can we help you today?", label="An integrated patient health assistant", color="t")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        card("🦠 Diseases", "Answer a few questions about how you feel and get a quick assessment.", "01", "#14463A")
    with col2:
        card("🥗 Nutrition", "Find your BMR, daily calories and a meal plan for your activity level.", "02", "#F2C14E")
    with col3:
        card("🏃 Sports", "Check if you are ready for a run and get a recovery plan after it.", "03", "#3D5A80")
    with col4:
        card("🩺 Clinic", "We send you to the right department and book your appointment.", "04", "#C2362B")

    st.write("")
    if not file_done:
        st.info("🗂️ Start with the Patient file tab, then pick a service.")
        st.button("Open patient file", on_click=go_to_patient_file)


elif page == "Patient file": # patient file page
    banner("Patient file", "Fill it one time and every service uses it", "00", "Step 1", "t")

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Patient ID", key="patient_id", placeholder="e.g. P-1001")
        st.number_input("Age", 1, 120, value=None, key="age", placeholder="e.g. 25")
        st.number_input("Weight (kg)", 20.0, 250.0, value=None, key="weight", placeholder="e.g. 70")
    with col2:
        st.text_input("Name", key="name", placeholder="e.g. Sara Alharbi")
        st.selectbox("Gender", ["male", "female"], index=None, key="gender", placeholder="e.g. male")
        st.number_input("Height (cm)", 100.0, 230.0, value=None, key="height", placeholder="e.g. 170")

    st.write("")
    if all(st.session_state.get(key) not in (None, "") for key in patient_keys):
        st.success("✅ Patient file saved. Pick a service from the menu on top.")
    else:
        st.caption("The grey text is only an example. Fill every field to unlock the services.")


elif page == "Diseases": # diseases page
    banner("Disease Assessment", "Tick what you are feeling right now", "01", "Live services", "g")
    need_patient_file()

    d = Diseases(patient_id, name, age, gender, {})
    d.display_questions() # the questions from the diseases class

    if st.button("Check"):
        d.display_info()


elif page == "Nutrition": # nutrition page
    banner("Nutrition", "Calories and meals based on how active you are", "02", "Live services", "g")
    need_patient_file()

    level_names = ["Low activity", "Lightly active", "Moderately active", "Very active", "Extra active"]
    level_name = st.select_slider("Activity level", options=level_names, value="Lightly active")
    activity_level = level_names.index(level_name) + 1 # the class needs a number from 1 to 5

    n = nutrition(name, age, gender, weight, height, activity_level)
    bmr, calories = n.calculate_calories()

    col1, col2 = st.columns(2)
    col1.metric("BMR", str(round(bmr)) + " kcal")
    col2.metric("Daily calories", str(round(calories)) + " kcal")

    meals = n.weight_loss_meals()
    st.subheader("🍽️ Weight loss meals (" + meals["level"].strip() + ")")
    st.text(meals["meals"])


elif page == "Sports": # sports page
    banner("Sports Readiness", "Are you ready for the run?", "03", "Live services", "g")
    need_patient_file()

    col1, col2 = st.columns(2)
    avg_sleep = col1.slider("Average sleep (hours)", 3.0, 12.0, 7.0, 0.5)
    activity = col2.selectbox("Activity (sedentary = 0 days, light = 1-2, moderate = 3-4, high = 5+)",
                              ["sedentary", "light", "moderate", "high"])

    s = SportService(name, age, height, weight, avg_sleep, activity)

    col1, col2 = st.columns(2)
    col1.metric("BMI", s.calc_bmi())
    col2.metric("Readiness", s.readiness_level())

    st.subheader("Your run")
    col1, col2 = st.columns(2)
    distance = col1.number_input("Distance (km)", 1.0, 50.0, 5.0)
    pace = col2.number_input("Pace (min per km)", 3.0, 15.0, 7.0)

    tips, fluids = s.recovery_plan(distance, pace)

    col1, col2 = st.columns(2)
    col1.metric("🔥 Calories burned", s.calories_burned(distance, pace))
    col2.metric("💧 Water to drink", str(fluids) + " L")

    st.subheader("Recovery plan")
    for tip in tips:
        st.write("-", tip)


elif page == "Clinic": # clinic page
    banner("Clinic & Booking", "Tell us your symptoms and we book you with the right doctor", "04", "Clinic & triage", "p")
    need_patient_file()

    # we save the patient in session_state because streamlit reruns the whole file on every click
    # and without it the queue number keeps going up
    if "clinic" not in st.session_state:
        st.session_state.clinic = Clinic(patient_id, name, age, gender, {}, False)
    c = st.session_state.clinic

    c.patient_id = patient_id # update the info if the user changes the sidebar
    c.name = name
    c.age = age
    c.gender = gender

    left, right = st.columns([3, 2])

    with left:
        c.display_questions() # this method comes from the diseases class
        c.has_insurance = st.checkbox("I have health insurance")

        department = c.pick_department()
        level = c.triage_level()
        st.markdown("**Department:** " + department + " &nbsp; | &nbsp; **Priority:** <span class='tag " + level + "'>" + level + "</span>",
                    unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        day = col1.selectbox("Day", Clinic.work_days)
        time = col2.selectbox("Time", Clinic.time_slots)

        if st.button("Book appointment"):
            booked, message = c.book_appointment(day, time)
            if booked == True:
                st.success(message)
            else:
                st.error(message)

    with right:
        summary = c.visit_summary()

        if summary == None: # no booking yet
            card("🎫 No booking yet", "Your ticket will show here after you book.", "TICKET", "#C2362B")
        else:
            rows = ""
            for key in summary: # make a row for every info in the ticket
                rows += '<div class="row"><span>' + key + '</span><span>' + str(summary[key]) + '</span></div>'
            st.markdown('<div class="ticket"><h3>🎫 Your ticket</h3>' + rows + '</div>', unsafe_allow_html=True)

            if st.button("New patient"): # start again with a new patient
                del st.session_state.clinic
                st.rerun()
