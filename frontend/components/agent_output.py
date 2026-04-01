"""
agt_sea — Agent Output Component

Displays a single agent output: metadata row (provider, model,
timestamp) + content. For Creative Director outputs, also renders
score, strengths, weaknesses, and direction.

Used inside expanders created by render_history(), and also by
standalone pages (Strategy, Creative) to display results.
"""

from __future__ import annotations

import streamlit as st

from agt_sea.models.state import AgentOutput


def render_agent_output(entry: AgentOutput) -> None:
    """Render a single agent output with metadata and content.

    Args:
        entry: The AgentOutput to display.
    """
    # --- Metadata row ---
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"**Provider:** {entry.provider.value}")
    col2.markdown(f"**Model:** {entry.model}")
    col3.markdown(
        f"**Date:** {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    st.markdown("---")

    # --- CD evaluation (structured output) ---
    if entry.evaluation is not None:
        score_col, detail_col = st.columns([1, 3])
        with score_col:
            st.metric("score", f"{entry.evaluation.score}/100")
        with detail_col:
            st.markdown("**Strengths:**")
            for s in entry.evaluation.strengths:
                st.markdown(f"- {s}")
            st.markdown("**Weaknesses:**")
            for w in entry.evaluation.weaknesses:
                st.markdown(f"- {w}")

        st.markdown(f"**Direction:** {entry.evaluation.direction}")

    # --- Content (strategist / creative) ---
    else:
        st.markdown(entry.content)
