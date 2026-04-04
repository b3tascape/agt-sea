"""
agt_sea — Streamlit Entry Point

Navigation shell: page config, theme loading, sidebar, and page routing.
All page-specific content lives in pages/*.py.

Run with: uv run streamlit run frontend/app.py
"""

import sys
from pathlib import Path

import streamlit as st

# Ensure agt_sea package is importable (needed for Streamlit Cloud).
# Page files loaded via st.Page() run in the same process, so this
# sys.path modification is already in effect when page code executes.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# ---------------------------------------------------------------------------
# Page config — must be the first Streamlit command
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="agt_sea",
    page_icon="🌊",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Theme — load from external CSS file
# ---------------------------------------------------------------------------

theme_css = (Path(__file__).parent / "themes" / "b3ta.css").read_text()
st.markdown(f"<style>{theme_css}</style>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Logo — st.logo() renders above st.navigation's page links natively
# ---------------------------------------------------------------------------

st.logo(
    str(Path(__file__).parent / "themes" / "logo.svg"),
    size="large",
)

# ---------------------------------------------------------------------------
# Sidebar — global parameters, footer
# ---------------------------------------------------------------------------

from components.sidebar import render_sidebar  # noqa: E402

render_sidebar()

# ---------------------------------------------------------------------------
# Navigation — visible modules only
# ---------------------------------------------------------------------------

pages = [
    st.Page("pages/strategy.py", title="Strategy"),
    st.Page("pages/creative.py", title="Creative"),
    st.Page("pages/workflow.py", title="Workflow"),
    st.Page("pages/tools.py", title="Tools"),
]

pg = st.navigation(pages)
pg.run()
