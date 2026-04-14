"""
agt_sea — Error State Component

Renders a failed run in place of the usual success output. Reads
``state.error`` (written by ``_safe_node`` in ``graph/workflow.py`` or
reconstructed by standalone pages via ``format_node_error``) and shows
the provider / model that were in use, so the user knows what to switch
in the sidebar before re-running.
"""

from __future__ import annotations

import streamlit as st

from agt_sea.config import get_llm_provider, get_model_name
from agt_sea.models.state import AgencyState


def render_error_state(state: AgencyState) -> None:
    """Render a failed pipeline run as an error panel.

    Args:
        state: The final (rehydrated) state with ``status == FAILED``
            and a populated ``error`` field.
    """
    st.markdown("### run failed")

    st.error(state.error or "Unknown failure (no error detail captured).")

    # Provider / model row — shows the user what was in use so they can
    # decide whether to switch in the sidebar before re-running. The
    # config-fallback branch is defence-in-depth: in practice the
    # sidebar always populates state.llm_provider / state.llm_model
    # before any run is invoked, so the ``or`` fallback is essentially
    # unreachable on the current flow. Kept so the component stays
    # robust if a page ever constructs an AgencyState without going
    # through the sidebar.
    provider = state.llm_provider or get_llm_provider()
    model = state.llm_model or get_model_name(provider)

    col_provider, col_model = st.columns(2)
    col_provider.markdown(f"**Provider:** {provider.value}")
    col_model.markdown(f"**Model:** {model}")

    st.caption(
        "Try again, or switch provider / model in the sidebar and re-run."
    )
