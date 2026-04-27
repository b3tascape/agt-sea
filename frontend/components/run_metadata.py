"""
agt_sea — Run Metadata Component

Renders the metrics for a pipeline run across two rows:
Row 1: iterations, history count, status.
Row 2: per-agent philosophies (3 for Standard 1.0, 4 for Standard 2.0).
"""

from __future__ import annotations

from typing import Literal

import streamlit as st

from agt_sea.models.state import AgencyState

from components.labels import CREATIVE_PHILOSOPHY_LABELS, STRATEGIC_PHILOSOPHY_LABELS


def render_run_metadata(
    state: AgencyState,
    mode: Literal["v1", "v2"],
) -> None:
    """Render the run metadata metrics rows.

    Args:
        state: The final (rehydrated) pipeline state.
        mode: Which pipeline this run belongs to. ``"v1"`` shows the
            three Standard 1.0 philosophy fields; ``"v2"`` shows the
            four Standard 2.0 philosophy fields (strategist, Creative 1,
            Creative 2, Creative Director — Grader is neutral by
            contract and excluded).
    """
    st.markdown("### run metadata")

    row1_col1, row1_col2, row1_col3 = st.columns(3)
    row1_col1.metric("iterations", state.iteration)
    row1_col2.metric("history", len(state.history))
    row1_col3.metric("status", state.status.value)

    if mode == "v1":
        c1, c2, c3 = st.columns(3)
        c1.metric(
            "strategist philosophy",
            STRATEGIC_PHILOSOPHY_LABELS.get(
                state.strategist_st1_strategic_philosophy, ""
            ),
        )
        c2.metric(
            "creative philosophy",
            CREATIVE_PHILOSOPHY_LABELS.get(
                state.creative_st1_creative_philosophy, ""
            ),
        )
        c3.metric(
            "cd philosophy",
            CREATIVE_PHILOSOPHY_LABELS.get(
                state.creative_director_st1_creative_philosophy, ""
            ),
        )
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "strategist philosophy",
            STRATEGIC_PHILOSOPHY_LABELS.get(
                state.strategist_st2_strategic_philosophy, ""
            ),
        )
        c2.metric(
            "creative 1 philosophy",
            CREATIVE_PHILOSOPHY_LABELS.get(
                state.creative_a_st2_creative_philosophy, ""
            ),
        )
        c3.metric(
            "creative 2 philosophy",
            CREATIVE_PHILOSOPHY_LABELS.get(
                state.creative_b_st2_creative_philosophy, ""
            ),
        )
        c4.metric(
            "cd philosophy",
            CREATIVE_PHILOSOPHY_LABELS.get(
                state.creative_director_st2_creative_philosophy, ""
            ),
        )
