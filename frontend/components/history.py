"""
agt_sea — History Component

Renders the full pipeline history as a sequence of labelled
expanders, each containing an agent output display.
"""

from __future__ import annotations

import streamlit as st

from agt_sea.models.state import AgentOutput, AgentRole

from components.agent_output import render_agent_output


def render_history(history: list[AgentOutput]) -> None:
    """Render pipeline history as labelled expanders.

    Args:
        history: Ordered list of AgentOutput entries from the pipeline run.
    """
    iteration = 0

    for entry in history:
        if entry.agent == AgentRole.STRATEGIST:
            with st.expander("strategist — creative brief"):
                render_agent_output(entry)

        elif entry.agent == AgentRole.CREATIVE:
            iteration += 1
            with st.expander(f"creative — iteration {iteration}"):
                render_agent_output(entry)

        elif entry.agent == AgentRole.CREATIVE_DIRECTOR:
            with st.expander(
                f"creative director — iteration {iteration} "
                f"· score: {entry.evaluation.score}/100"
            ):
                render_agent_output(entry)
