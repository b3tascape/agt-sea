"""
agt_sea — Strategy Page

Standalone strategist: user provides a client brief, gets a
structured creative brief. Calls run_strategist() directly —
no LangGraph orchestration needed for a single agent.
"""

from __future__ import annotations

import streamlit as st

from agt_sea.agents.strategist import run_strategist
from agt_sea.graph.workflow import format_node_error
from agt_sea.models.state import AgencyState, WorkflowStatus

from components.agent_output import render_agent_output
from components.error_state import render_error_state
from components.footer import render_footer
from components.run_guard import check_run_allowed, render_run_limit_reached

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
    if not check_run_allowed():
        render_run_limit_reached()
        st.stop()
    st.session_state.strategy_brief_input = brief_text
    # Clear stale result so a failed re-run doesn't show the prior output.
    st.session_state.pop("strategy_result", None)
    state = AgencyState(
        client_brief=brief_text,
        strategic_philosophy=st.session_state.strategic_philosophy,
        creative_philosophy=st.session_state.creative_philosophy,
        cd_philosophy=st.session_state.cd_philosophy,
        llm_provider=st.session_state.llm_provider,
        llm_model=st.session_state.llm_model,
    )
    try:
        with st.spinner("strategist is writing the creative brief..."):
            result = run_strategist(state)
    except Exception as exc:
        # Standalone pages don't go through _safe_node, so we reconstruct
        # the same state.error format here via format_node_error — the
        # shared helper that keeps this in sync with the graph path.
        state.error = format_node_error("run_strategist", exc)
        state.status = WorkflowStatus.FAILED
        result = state
    st.session_state.strategy_result = result

# ---------------------------------------------------------------------------
# Render persisted result (survives page switches)
# ---------------------------------------------------------------------------

if "strategy_result" in st.session_state:
    result = st.session_state.strategy_result
    st.markdown("---")

    if result.status == WorkflowStatus.FAILED:
        render_error_state(result)
        render_footer()
    else:
        st.markdown("### creative brief")
        render_agent_output(result.history[-1])

        if st.toggle("</> & copy", key="strategy_copy_toggle"):
            st.code(result.history[-1].content, language="markdown")

        render_footer()
