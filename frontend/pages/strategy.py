"""
agt_sea — Strategy Page

Standalone strategist: user provides a client brief, gets a
structured creative brief. Calls run_strategist() directly —
no LangGraph orchestration needed for a single agent.
"""

from __future__ import annotations

import streamlit as st

from agt_sea.agents.strategist import run_strategist
from agt_sea.models.state import AgencyState

from components.agent_output import render_agent_output
from components.footer import render_footer

# ---------------------------------------------------------------------------
# Page content
# ---------------------------------------------------------------------------

st.title("_strategy")
st.markdown(
    "Submit a client brief and our **strategist** agent will transform it "
    "into a structured creative brief."
)

brief_text = st.text_area(
    "CLIENT BRIEF",
    height=200,
    value=st.session_state.get("strategy_brief_input", ""),
    placeholder=(
        "Describe your brand, target audience, campaign objectives, "
        "channels, budget, and timeline..."
    ),
)

run_button = st.button(
    "RUN STRATEGIST",
    type="primary",
    disabled=not brief_text,
)

# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

if run_button and brief_text:
    st.session_state.strategy_brief_input = brief_text
    with st.spinner("strategist is writing the creative brief..."):
        state = AgencyState(
            client_brief=brief_text,
            strategic_philosophy=st.session_state.strategic_philosophy,
            creative_philosophy=st.session_state.creative_philosophy,
            cd_philosophy=st.session_state.cd_philosophy,
            llm_provider=st.session_state.llm_provider,
            llm_model=st.session_state.llm_model,
        )
        result = run_strategist(state)
    st.session_state.strategy_result = result

# ---------------------------------------------------------------------------
# Render persisted result (survives page switches)
# ---------------------------------------------------------------------------

if "strategy_result" in st.session_state:
    result = st.session_state.strategy_result
    st.markdown("---")
    st.markdown("### creative brief")
    render_agent_output(result.history[-1])

    if st.toggle("</> & copy", key="strategy_copy_toggle"):
        st.code(result.history[-1].content, language="markdown")

    render_footer()
