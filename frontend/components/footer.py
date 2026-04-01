"""
agt_sea — Footer Component

Renders the SM λ © badge used at the bottom of pages.
"""

from __future__ import annotations

import streamlit as st


def render_footer() -> None:
    """Render the footer badge."""
    st.markdown(
        '<div class="footer-badge">SM λ ©</div>',
        unsafe_allow_html=True,
    )
