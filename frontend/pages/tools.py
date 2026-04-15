"""agt_sea — Tools"""

import streamlit as st

st.title("_tools")

st.markdown("Tools for creative exploration.")

# Accent theme override — applied after title so it doesn't affect layout position
st.markdown("""
<style>
    .stApp { background-color: var(--accent-aquagreen) !important; }
    section[data-testid="stSidebar"] { background-color: var(--accent-aquagreen) !important; }
</style>
""", unsafe_allow_html=True)

st.info("This module is in development.")

# TODO: wire check_run_allowed() into tool agent run handlers when implemented.
