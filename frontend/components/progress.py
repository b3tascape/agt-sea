"""
agt_sea — Progress Component

Renders a live status container for a single graph node during
pipeline execution. Called once per node event in the streaming loop.
"""

from __future__ import annotations

import streamlit as st


_NODE_LABELS: dict[str, tuple[str, str]] = {
    "strategist": ("strategist", "writing creative brief..."),
    "creative": ("creative", "generating ideas..."),
    "creative_director": ("creative director", "evaluating work..."),
    "check_iterations": ("iteration check", "checking iteration limit..."),
    "finalise_approved": ("approved", "creative work approved."),
    "finalise_max_iterations": ("max iterations", "selecting best work..."),
}


def render_node_progress(node_name: str, node_output: dict) -> None:
    """Render a status container for a single graph node event.

    Args:
        node_name: The graph node name (e.g. "strategist", "creative").
        node_output: The state update dict emitted by this node.
    """
    label, description = _NODE_LABELS.get(
        node_name, (node_name, "processing...")
    )

    with st.status(f"{label}", expanded=False) as status:
        st.write(description)

        if node_name == "strategist":
            st.markdown("**creative brief (preview):**")
            st.markdown(
                node_output.get("creative_brief", "")[:500] + "..."
            )
            status.update(label=f"{label} ✓", state="complete")

        elif node_name == "creative":
            iteration = node_output.get("iteration", 0)
            st.markdown(f"**iteration {iteration} — concepts (preview):**")
            st.markdown(
                node_output.get("creative_concept", "")[:500] + "..."
            )
            status.update(
                label=f"{label} · iteration {iteration} ✓",
                state="complete",
            )

        elif node_name == "creative_director":
            evaluation = node_output.get("cd_evaluation")
            if evaluation:
                st.metric("score", f"{evaluation.score}/100")
                st.markdown(f"**direction:** {evaluation.direction}")
            status.update(label=f"{label} ✓", state="complete")

        elif node_name in ("finalise_approved", "finalise_max_iterations"):
            status.update(label=f"{label}", state="complete")

        else:
            status.update(label=f"{label} ✓", state="complete")
