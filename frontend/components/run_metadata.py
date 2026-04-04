"""
agt_sea — Run Metadata Component

Renders the metrics row at the bottom of a pipeline run:
iterations, history count, philosophy, and status.
"""

from __future__ import annotations

import streamlit as st

from components.labels import PHILOSOPHY_LABELS


def render_run_metadata(state: dict) -> None:
    """Render the run metadata metrics row.

    Args:
        state: The final pipeline state dict containing iteration,
            history, creative_philosophy, and status fields.
    """
    st.markdown("### run metadata")
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("iterations", state.get("iteration", 0))
    col2.metric("history", len(state.get("history", [])))

    philosophy = state.get("creative_philosophy")
    col3.metric("philosophy", PHILOSOPHY_LABELS.get(philosophy, ""))

    status = state.get("status")
    col4.metric("status", status.value if status else "")
