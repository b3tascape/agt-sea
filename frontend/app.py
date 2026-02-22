"""
agt_sea — Streamlit Frontend

Run with: uv run streamlit run frontend/app.py
"""

import streamlit as st

from agt_sea.graph.workflow import build_graph
from agt_sea.models.state import (
    AgencyState,
    AgentRole,
    CreativePhilosophy,
    WorkflowStatus,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="agt_sea",
    page_icon="🌊",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Sidebar — inputs
# ---------------------------------------------------------------------------

st.sidebar.title("🌊 agt_sea")
st.sidebar.markdown("*a creative agency framework*")
st.sidebar.markdown("---")

# Creative philosophy selector
philosophy_labels = {
    CreativePhilosophy.BOLD_AND_DISRUPTIVE: "Bold & Disruptive",
    CreativePhilosophy.MINIMAL_AND_REFINED: "Minimal & Refined",
    CreativePhilosophy.EMOTIONALLY_DRIVEN: "Emotionally Driven",
    CreativePhilosophy.DATA_LED: "Data Led",
    CreativePhilosophy.CULTURALLY_PROVOCATIVE: "Culturally Provocative",
}

selected_philosophy = st.sidebar.selectbox(
    "Creative Philosophy",
    options=list(philosophy_labels.keys()),
    format_func=lambda x: philosophy_labels[x],
    help="Sets the Creative Director's evaluation lens.",
)

st.sidebar.markdown("---")
st.sidebar.markdown("**How it works:**")
st.sidebar.markdown(
    "Submit a client brief and watch three AI agents "
    "collaborate — a Strategist writes the creative brief, a Creative "
    "generates ideas, and a Creative Director evaluates the work."
)

# ---------------------------------------------------------------------------
# Main area — brief input
# ---------------------------------------------------------------------------

st.title("🌊 agt_sea")
st.markdown("### Submit your client brief")

brief_text = st.text_area(
    "Client Brief",
    height=200,
    placeholder=(
        "Describe your brand, target audience, campaign objectives, "
        "channels, budget, and timeline..."
    ),
)

run_button = st.button("Run Creative Pipeline", type="primary", disabled=not brief_text)

# ---------------------------------------------------------------------------
# Pipeline execution with live progress
# ---------------------------------------------------------------------------

if run_button and brief_text:
    # Build a fresh graph for each run
    graph = build_graph()

    initial_state = AgencyState(
        client_brief=brief_text,
        creative_philosophy=selected_philosophy,
    )

    # Progress tracking
    progress_container = st.container()
    results_container = st.container()

    with progress_container:
        st.markdown("---")
        st.markdown("### Pipeline Progress")

        # Stream through the graph node by node
        final_state = None
        node_labels = {
            "strategist": ("📋 Strategist", "Writing creative brief..."),
            "creative": ("💡 Creative", "Generating ideas..."),
            "creative_director": ("🎯 Creative Director", "Evaluating work..."),
            "check_iterations": ("🔄 Iteration Check", "Checking iteration limit..."),
            "finalise_approved": ("✅ Approved", "Creative work approved!"),
            "finalise_max_iterations": ("⚠️ Max Iterations", "Selecting best work..."),
        }

        for event in graph.stream(initial_state):
            # Each event is a dict with the node name as key
            for node_name, node_output in event.items():
                label, description = node_labels.get(
                    node_name, (node_name, "Processing...")
                )

                with st.status(f"{label}", expanded=False) as status:
                    st.write(description)

                    if node_name == "strategist":
                        st.markdown("**Creative Brief (preview):**")
                        st.markdown(node_output.get("creative_brief", "")[:500] + "...")
                        status.update(label=f"{label} ✓", state="complete")

                    elif node_name == "creative":
                        iteration = node_output.get("iteration", 0)
                        st.markdown(f"**Iteration {iteration} — Concepts (preview):**")
                        st.markdown(node_output.get("creative_concept", "")[:500] + "...")
                        status.update(label=f"{label} (Iteration {iteration}) ✓", state="complete")

                    elif node_name == "creative_director":
                        evaluation = node_output.get("cd_evaluation")
                        if evaluation:
                            st.metric("Score", f"{evaluation.score}/100")
                            st.markdown(f"**Direction:** {evaluation.direction}")
                        status.update(label=f"{label} ✓", state="complete")

                    elif node_name in ("finalise_approved", "finalise_max_iterations"):
                        status.update(label=f"{label}", state="complete")

                    else:
                        status.update(label=f"{label} ✓", state="complete")

                # Keep track of the latest state
                final_state = node_output

    # ---------------------------------------------------------------------------
    # Results — expandable history and final output
    # ---------------------------------------------------------------------------

    if final_state:
        with results_container:
            st.markdown("---")

            # Final output
            status = final_state.get("status")
            if status == WorkflowStatus.APPROVED:
                st.success("✅ Creative work APPROVED")
            elif status == WorkflowStatus.MAX_ITERATIONS_REACHED:
                st.warning("⚠️ Max iterations reached — showing best scoring idea")

            st.markdown("### Final Creative Concept")
            st.markdown(final_state.get("creative_concept", ""))

            # Pipeline history
            st.markdown("---")
            st.markdown("### Pipeline History")

            history = final_state.get("history", [])
            iteration = 0

            for entry in history:
                if entry.agent == AgentRole.STRATEGIST:
                    with st.expander("📋 Strategist — Creative Brief"):
                        col1, col2, col3 = st.columns(3)
                        col1.markdown(f"**Provider:** {entry.provider.value}")
                        col2.markdown(f"**Model:** {entry.model}")
                        col3.markdown(
                            f"**Date:** {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        st.markdown("---")
                        st.markdown(entry.content)

                elif entry.agent == AgentRole.CREATIVE:
                    iteration += 1
                    with st.expander(
                        f"💡 Creative — Iteration {iteration}"
                    ):
                        col1, col2, col3 = st.columns(3)
                        col1.markdown(f"**Provider:** {entry.provider.value}")
                        col2.markdown(f"**Model:** {entry.model}")
                        col3.markdown(
                            f"**Date:** {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        st.markdown("---")
                        st.markdown(entry.content)

                elif entry.agent == AgentRole.CREATIVE_DIRECTOR:
                    with st.expander(
                        f"🎯 Creative Director — Iteration {iteration} "
                        f"(Score: {entry.evaluation.score}/100)"
                    ):
                        col1, col2, col3 = st.columns(3)
                        col1.markdown(f"**Provider:** {entry.provider.value}")
                        col2.markdown(f"**Model:** {entry.model}")
                        col3.markdown(
                            f"**Date:** {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        st.markdown("---")

                        score_col, detail_col = st.columns([1, 3])
                        with score_col:
                            st.metric("Score", f"{entry.evaluation.score}/100")
                        with detail_col:
                            st.markdown("**Strengths:**")
                            for s in entry.evaluation.strengths:
                                st.markdown(f"- {s}")
                            st.markdown("**Weaknesses:**")
                            for w in entry.evaluation.weaknesses:
                                st.markdown(f"- {w}")

                        st.markdown(f"**Direction:** {entry.evaluation.direction}")

            # Run metadata
            st.markdown("---")
            st.markdown("### Run Metadata")
            meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
            meta_col1.metric("Iterations", final_state.get("iteration", 0))
            meta_col2.metric("History Entries", len(history))
            meta_col3.metric(
                "Philosophy",
                philosophy_labels.get(selected_philosophy, ""),
            )
            meta_col4.metric("Status", final_state.get("status", "").value)
