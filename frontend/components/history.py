"""
agt_sea — History Component

Renders the full pipeline history as a sequence of labelled
expanders, each containing an agent output display.

Handles both Standard 1.0 roles (STRATEGIST, CREATIVE,
CREATIVE_DIRECTOR) and Standard 2.0 roles (CREATIVE_1, CREATIVE_2,
CD_GRADER, CD_FEEDBACK, CD_SYNTHESIS). Iteration counters are scoped
to the creative agent per workflow version so labels read naturally
in either timeline.
"""

from __future__ import annotations

import streamlit as st

from agt_sea.models.state import AgentOutput, AgentRole

from components.agent_output import render_agent_output


def render_history(history: list[AgentOutput]) -> None:
    """Render pipeline history as labelled expanders.

    Args:
        history: Ordered list of AgentOutput entries from the pipeline
            run. May contain Standard 1.0 or Standard 2.0 entries (or
            both in principle — the label routing dispatches per-role).
    """
    v1_iteration = 0  # bumped by CREATIVE entries
    v2_iteration = 0  # bumped by CREATIVE_2 entries

    for entry in history:
        # --- Standard 1.0 ---
        if entry.agent == AgentRole.STRATEGIST:
            with st.expander("strategist — creative brief"):
                render_agent_output(entry)

        elif entry.agent == AgentRole.CREATIVE:
            v1_iteration += 1
            with st.expander(f"creative — iteration {v1_iteration}"):
                render_agent_output(entry)

        elif entry.agent == AgentRole.CREATIVE_DIRECTOR:
            score_suffix = (
                f" · score: {entry.evaluation.score}/100"
                if entry.evaluation is not None
                else ""
            )
            with st.expander(
                f"creative director — iteration {v1_iteration}{score_suffix}"
            ):
                render_agent_output(entry)

        # --- Standard 2.0 ---
        elif entry.agent == AgentRole.CREATIVE_1:
            with st.expander("creative 1 — territories"):
                render_agent_output(entry)

        elif entry.agent == AgentRole.CREATIVE_2:
            v2_iteration += 1
            with st.expander(f"creative 2 — iteration {v2_iteration}"):
                render_agent_output(entry)

        elif entry.agent == AgentRole.CD_GRADER:
            with st.expander(f"cd grader — iteration {v2_iteration}"):
                render_agent_output(entry)

        elif entry.agent == AgentRole.CD_FEEDBACK:
            with st.expander(f"cd feedback — iteration {v2_iteration}"):
                render_agent_output(entry)

        elif entry.agent == AgentRole.CD_SYNTHESIS:
            with st.expander("cd synthesis — final recommendation"):
                render_agent_output(entry)
