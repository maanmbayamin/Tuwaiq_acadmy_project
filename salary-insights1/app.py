import streamlit as st

st.set_page_config(page_title="Data & AI Salaries", page_icon=":material/payments:", layout="wide",
                   initial_sidebar_state="collapsed")

from utils import CURRENCIES  # noqa: E402  (after set_page_config)

pages = [
    st.Page("views/overview.py", title="Overview", icon=":material/home:", default=True),
    st.Page("views/the_data.py", title="The Data", icon=":material/table_chart:"),
    st.Page("views/explore.py", title="Explore Salaries", icon=":material/query_stats:"),
    st.Page("views/saudi.py", title="Saudi Arabia vs the World", icon=":material/public:"),
    st.Page("views/model.py", title="How the Model Works", icon=":material/model_training:"),
    st.Page("views/estimate.py", title="Estimate a Salary", icon=":material/calculate:"),
]
pg = st.navigation(pages, position="top")

# Currency switch on the top right of every page
_, right = st.columns([3, 1])
with right:
    st.segmented_control("Show amounts in", CURRENCIES, key="currency", default=CURRENCIES[0],
                         required=True, width="stretch",
                         help="1 USD = 3.75 SAR (fixed peg). Yearly USD is divided by 12 for monthly SAR.")

pg.run()
