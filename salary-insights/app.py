import streamlit as st

st.set_page_config(page_title="Data & AI Salaries", page_icon=":material/payments:", layout="wide")

from utils import CURRENCIES  # noqa: E402  (after set_page_config)

pages = [
    st.Page("views/overview.py", title="Overview", icon=":material/home:", default=True),
    st.Page("views/the_data.py", title="The Data", icon=":material/table_chart:"),
    st.Page("views/explore.py", title="Explore Salaries", icon=":material/query_stats:"),
    st.Page("views/saudi.py", title="Saudi Arabia vs the World", icon=":material/public:"),
    st.Page("views/model.py", title="How the Prediction Model Works", icon=":material/model_training:"),
    st.Page("views/estimate.py", title="Estimate a Salary", icon=":material/calculate:"),
]
pg = st.navigation(pages)

with st.sidebar:
    st.radio("Show salaries in", CURRENCIES, key="currency",
             help="1 USD = 3.75 SAR (fixed peg). Yearly USD is divided by 12 for monthly SAR.")
    st.caption("Data: 13,972 global salary records (2020 to 2024) + 11 Saudi benchmark ranges.")

pg.run()
