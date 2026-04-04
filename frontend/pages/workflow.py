"""
agt_sea — Workflow Page

Full creative campaign pipeline: Strategist → Creative → CD loop.
Uses LangGraph for orchestration with live streaming progress.

Tab-scaffolded for future workflows — currently one tab
("Creative Campaign") containing the existing pipeline.
"""

from __future__ import annotations

import streamlit as st

from agt_sea.graph.workflow import build_graph
from agt_sea.models.state import AgencyState, WorkflowStatus

from components.footer import render_footer
from components.history import render_history
from components.progress import render_node_progress
from components.run_metadata import render_run_metadata

# ---------------------------------------------------------------------------
# Tab scaffold — add new workflow tabs here
# ---------------------------------------------------------------------------

(tab_campaign,) = st.tabs(["Creative Campaign"])

with tab_campaign:
    st.title("{ workflow }")
    st.markdown("### submit your brief")

    brief_text = st.text_area(
        "CLIENT BRIEF",
        height=200,
        placeholder=(
            "Describe your brand, target audience, campaign objectives, "
            "channels, budget, and timeline..."
        ),
    )

    run_button = st.button(
        "RUN PIPELINE",
        type="primary",
        disabled=not brief_text,
    )

    # -------------------------------------------------------------------
    # Pipeline execution with live progress
    # -------------------------------------------------------------------

    if run_button and brief_text:
        graph = build_graph()

        initial_state = AgencyState(
            client_brief=brief_text,
            creative_philosophy=st.session_state.creative_philosophy,
            max_iterations=st.session_state.max_iterations,
            approval_threshold=st.session_state.approval_threshold,
            llm_provider=st.session_state.llm_provider,
            llm_model=st.session_state.llm_model,
        )

        progress_container = st.container()
        results_container = st.container()

        with progress_container:
            st.markdown("---")
            st.markdown("### pipeline executing...")

            final_state = None

            for event in graph.stream(initial_state):
                for node_name, node_output in event.items():
                    render_node_progress(node_name, node_output)
                    final_state = node_output

        # ---------------------------------------------------------------
        # Results
        # ---------------------------------------------------------------

        if final_state:
            with results_container:
                st.markdown("---")

                status = final_state.get("status")
                if status == WorkflowStatus.APPROVED:
                    st.success("creative work approved.")
                elif status == WorkflowStatus.MAX_ITERATIONS_REACHED:
                    st.warning(
                        "max iterations reached — showing best scoring idea."
                    )

                st.markdown("### final creative concept")
                st.markdown(final_state.get("creative_concept", ""))

                st.markdown("---")
                st.markdown("### pipeline history")
                render_history(final_state.get("history", []))

                st.markdown("---")
                render_run_metadata(final_state)

                render_footer()
