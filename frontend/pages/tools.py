"""agt_sea — Tools"""

import streamlit as st

# Apply accent theme override
st.markdown("""
<style>
    .stApp { background-color: var(--accent-aquagreen) !important; }
    section[data-testid="stSidebar"] { background-color: var(--accent-aquagreen) !important; }
</style>
""", unsafe_allow_html=True)

st.title("{ tools }")
st.info("This module is in development.")
