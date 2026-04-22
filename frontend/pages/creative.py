"""
agt_sea — Creative Page

Standalone creative page. Two tabs:

* **c1_territory** (default, left) — Standard 2.0 territory generation
  via the creative_1 agent. User picks ``num_territories`` (1–12), the
  agent returns that many independent creative territories rendered as
  modular cards.
* **c0_original** (right) — the original Standard 1.0 creative agent,
  single-shot, producing three campaign concepts from a creative brief.

Each tab maintains its own input + result in ``st.session_state`` so
switching tabs doesn't wipe the other tab's work.
"""

from __future__ import annotations

import streamlit as st

from agt_sea.agents.creative import run_creative
from agt_sea.agents.creative1 import run_creative1
from agt_sea.graph.workflow import format_node_error
from agt_sea.models.state import AgencyState, WorkflowStatus

from components.agent_output import render_agent_output
from components.error_state import render_error_state
from components.footer import render_footer
from components.run_guard import check_run_allowed, render_run_limit_reached
from components.territory_cards import render_territory_cards


# ---------------------------------------------------------------------------
# Page shell
# ---------------------------------------------------------------------------

st.title("_creative")

tab_c1, tab_c0 = st.tabs(["c1_territory", "c0_original"])


# ---------------------------------------------------------------------------
# Tab: c1_territory — Standard 2.0 territory generation
# ---------------------------------------------------------------------------

def _render_c1_territory() -> None:
    """Render the creative_1 territory-generation tab."""
    st.markdown(
        "Submit a creative brief and **creative_1** will generate a set of "
        "distinct creative territories, each a tight artifact with a title, "
        "a 1–2 sentence core idea, and a brief rationale. Pick the count "
        "below (1–12)."
    )

    num_territories = st.number_input(
        "NUM TERRITORIES",
        min_value=1,
        max_value=12,
        value=st.session_state.get("num_territories", 3),
        step=1,
        help="How many distinct territories creative_1 should generate.",
    )
    st.session_state.num_territories = int(num_territories)

    brief_text = st.text_area(
        "CREATIVE BRIEF",
        height=200,
        value=st.session_state.get("c1_brief_input", ""),
        placeholder=(
            "Paste a creative brief — challenge, audience, insight, "
            "proposition, and tone..."
        ),
        key="c1_brief_textarea",
    )

    run_button = st.button(
        "RUN CREATIVE 1",
        type="primary",
        disabled=not brief_text,
        key="c1_run_button",
    )

    # --- Execution ---
    if run_button and brief_text:
        if not check_run_allowed():
            render_run_limit_reached()
            st.stop()
        st.session_state.c1_brief_input = brief_text
        # Clear stale result so a failed re-run doesn't show prior output.
        st.session_state.pop("c1_result", None)
        state = AgencyState(
            creative_brief=brief_text,
            num_territories=int(num_territories),
            strategic_philosophy=st.session_state.strategic_philosophy,
            creative_philosophy=st.session_state.creative_philosophy,
            cd_philosophy=st.session_state.cd_philosophy,
            creative1_provenance=st.session_state.creative1_provenance,
            creative1_taste=st.session_state.creative1_taste,
            creative1_temperature=st.session_state.creative1_temperature,
            llm_provider=st.session_state.llm_provider,
            llm_model=st.session_state.llm_model,
        )
        try:
            with st.spinner("creative_1 is generating territories..."):
                result = run_creative1(state)
        except Exception as exc:
            # Standalone pages don't go through _safe_node, so we
            # reconstruct the same state.error format here via
            # format_node_error — the shared helper keeps this in sync
            # with the graph path.
            state.error = format_node_error("run_creative1", exc)
            state.status = WorkflowStatus.FAILED
            result = state
        st.session_state.c1_result = result

    # --- Persisted result (survives page switches) ---
    if "c1_result" in st.session_state:
        result = st.session_state.c1_result
        st.markdown("---")

        if result.status == WorkflowStatus.FAILED:
            render_error_state(result)
            render_footer()
        else:
            st.markdown(f"### {len(result.territories)} territories")
            render_territory_cards(result.territories)

            if st.toggle("</> & copy", key="c1_copy_toggle"):
                st.code(result.history[-1].content, language="markdown")

            render_footer()


# ---------------------------------------------------------------------------
# Tab: c0_original — Standard 1.0 creative agent (unchanged)
# ---------------------------------------------------------------------------

def _render_c0_original() -> None:
    """Render the original Standard 1.0 creative tab."""
    st.markdown(
        "Submit a creative brief and **creative_0** agent will generate three "
        "distinct campaign concepts, each with a title, core idea, "
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
        key="c0_brief_textarea",
    )

    run_button = st.button(
        "RUN CREATIVE",
        type="primary",
        disabled=not brief_text,
        key="c0_run_button",
    )

    if run_button and brief_text:
        if not check_run_allowed():
            render_run_limit_reached()
            st.stop()
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
            state.error = format_node_error("run_creative", exc)
            state.status = WorkflowStatus.FAILED
            result = state
        st.session_state.creative_result = result

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


with tab_c1:
    _render_c1_territory()

with tab_c0:
    _render_c0_original()
