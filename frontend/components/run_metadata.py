"""
agt_sea — Run Metadata Component

Renders the metrics for a pipeline run across two rows:
Row 1: iterations, history count, status.
Row 2: strategic, creative, and cd philosophies.
"""

from __future__ import annotations

import streamlit as st

from agt_sea.models.state import AgencyState

from components.labels import CREATIVE_PHILOSOPHY_LABELS, STRATEGIC_PHILOSOPHY_LABELS


def render_run_metadata(state: AgencyState) -> None:
    """Render the run metadata metrics rows.

    Args:
        state: The final (rehydrated) pipeline state.
    """
    st.markdown("### run metadata")

    row1_col1, row1_col2, row1_col3 = st.columns(3)
    row1_col1.metric("iterations", state.iteration)
    row1_col2.metric("history", len(state.history))
    row1_col3.metric("status", state.status.value)

    row2_col1, row2_col2, row2_col3 = st.columns(3)
    row2_col1.metric(
        "strat philosophy",
        STRATEGIC_PHILOSOPHY_LABELS.get(state.strategic_philosophy, ""),
    )
    row2_col2.metric(
        "creative philosophy",
        CREATIVE_PHILOSOPHY_LABELS.get(state.creative_philosophy, ""),
    )
    row2_col3.metric(
        "cd philosophy",
        CREATIVE_PHILOSOPHY_LABELS.get(state.cd_philosophy, ""),
    )
