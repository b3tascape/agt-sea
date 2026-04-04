"""
agt_sea — Creative Page

Standalone creative: user provides a creative brief, gets three
distinct campaign concepts. Calls run_creative() directly —
single-shot only, no CD loop, no iteration.
"""

from __future__ import annotations

import streamlit as st

from agt_sea.agents.creative import run_creative
from agt_sea.models.state import AgencyState

from components.agent_output import render_agent_output
from components.footer import render_footer

# ---------------------------------------------------------------------------
# Page content
# ---------------------------------------------------------------------------

st.title("{ agt_sea }")
st.markdown("### creative")
st.markdown(
    "Submit a creative brief and the **creative** will generate three "
    "distinct campaign concepts — each with a title, core idea, "
    "execution, and rationale."
)

brief_text = st.text_area(
    "CREATIVE BRIEF",
    height=200,
    placeholder=(
        "Paste a creative brief — challenge, audience, insight, "
        "proposition, and tone..."
    ),
)

run_button = st.button(
    "RUN CREATIVE",
    type="primary",
    disabled=not brief_text,
)

# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

if run_button and brief_text:
    with st.spinner("creative is generating concepts..."):
        state = AgencyState(
            creative_brief=brief_text,
            creative_philosophy=st.session_state.creative_philosophy,
            llm_provider=st.session_state.llm_provider,
            llm_model=st.session_state.llm_model,
        )
        result = run_creative(state)

    st.markdown("---")
    st.markdown("### creative concepts")
    render_agent_output(result.history[-1])

    render_footer()
