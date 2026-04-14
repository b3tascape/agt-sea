"""
agt_sea — Creative Page

Standalone creative: user provides a creative brief, gets three
distinct campaign concepts. Calls run_creative() directly —
single-shot only, no CD loop, no iteration.
"""

from __future__ import annotations

import streamlit as st

from agt_sea.agents.creative import run_creative
from agt_sea.graph.workflow import format_node_error
from agt_sea.models.state import AgencyState, WorkflowStatus

from components.agent_output import render_agent_output
from components.error_state import render_error_state
from components.footer import render_footer

# ---------------------------------------------------------------------------
# Page content
# ---------------------------------------------------------------------------

st.title("_creative")
st.markdown(
    "Submit a creative brief and our **creative** agent will generate three "
    "distinct campaign concepts — each with a title, core idea, "
    "execution, and rationale."
)

brief_text = st.text_area(
    "CREATIVE BRIEF",
    height=200,
    value=st.session_state.get("creative_brief_input", ""),
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
    st.session_state.creative_brief_input = brief_text
    # Clear stale result so a failed re-run doesn't show the prior output.
    st.session_state.pop("creative_result", None)
    state = AgencyState(
        creative_brief=brief_text,
        strategic_philosophy=st.session_state.strategic_philosophy,
        creative_philosophy=st.session_state.creative_philosophy,
        cd_philosophy=st.session_state.cd_philosophy,
        llm_provider=st.session_state.llm_provider,
        llm_model=st.session_state.llm_model,
    )
    try:
        with st.spinner("creative is generating concepts..."):
            result = run_creative(state)
    except Exception as exc:
        # Standalone pages don't go through _safe_node, so we reconstruct
        # the same state.error format here via format_node_error — the
        # shared helper that keeps this in sync with the graph path.
        state.error = format_node_error("run_creative", exc)
        state.status = WorkflowStatus.FAILED
        result = state
    st.session_state.creative_result = result

# ---------------------------------------------------------------------------
# Render persisted result (survives page switches)
# ---------------------------------------------------------------------------

if "creative_result" in st.session_state:
    result = st.session_state.creative_result
    st.markdown("---")

    if result.status == WorkflowStatus.FAILED:
        render_error_state(result)
        render_footer()
    else:
        st.markdown("### creative concepts")
        render_agent_output(result.history[-1])

        if st.toggle("</> & copy", key="creative_copy_toggle"):
            st.code(result.history[-1].content, language="markdown")

        render_footer()
