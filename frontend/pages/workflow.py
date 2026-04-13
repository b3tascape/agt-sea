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

st.title("_workflow")

(tab_campaign,) = st.tabs(["Creative Campaign"])

with tab_campaign:
    st.markdown(
        "Submit a client brief and our **strategist**, **creative** and "
        "**creative director** agents will collaborate to deliver a "
        "creative campaign concept."
    )

    brief_text = st.text_area(
        "CLIENT BRIEF",
        height=200,
        value=st.session_state.get("workflow_brief_input", ""),
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
        st.session_state.workflow_brief_input = brief_text
        graph = build_graph()

        initial_state = AgencyState(
            client_brief=brief_text,
            strategic_philosophy=st.session_state.strategic_philosophy,
            creative_philosophy=st.session_state.creative_philosophy,
            cd_philosophy=st.session_state.cd_philosophy,
            max_iterations=st.session_state.max_iterations,
            approval_threshold=st.session_state.approval_threshold,
            llm_provider=st.session_state.llm_provider,
            llm_model=st.session_state.llm_model,
        )

        progress_container = st.container()

        with progress_container:
            st.markdown("---")
            st.markdown("### pipeline executing...")

            # LangGraph's stream yields per-node dict updates. We
            # accumulate them into a running dict and then rehydrate to
            # an AgencyState at the end so downstream code can use
            # attribute access and typed nested models.
            accumulated: dict = {}

            for event in graph.stream(initial_state):
                for node_name, node_output in event.items():
                    render_node_progress(node_name, node_output)
                    accumulated.update(node_output)

            if accumulated:
                st.session_state.workflow_result = AgencyState.model_validate(
                    accumulated
                )

    # -------------------------------------------------------------------
    # Render persisted result (survives page switches)
    # -------------------------------------------------------------------

    if "workflow_result" in st.session_state:
        final_state = st.session_state.workflow_result

        st.markdown("---")

        if final_state.status == WorkflowStatus.APPROVED:
            st.success("creative work approved.")
        elif final_state.status == WorkflowStatus.MAX_ITERATIONS_REACHED:
            st.warning(
                "max iterations reached — showing best scoring idea."
            )
        elif final_state.status == WorkflowStatus.FAILED:
            # Step 6 replaces this with the proper error_state component.
            st.error(final_state.error or "run failed.")

        st.markdown("### final creative concept")
        st.markdown(final_state.creative_concept or "")

        st.markdown("---")
        st.markdown("### pipeline history")
        render_history(final_state.history)

        st.markdown("---")
        render_run_metadata(final_state)

        render_footer()
