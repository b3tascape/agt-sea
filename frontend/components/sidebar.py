"""
agt_sea — Sidebar Component

Renders the sidebar: logo, global parameters, and footer.
Writes all selections to st.session_state so pages can read them.
"""

from __future__ import annotations

import os

import streamlit as st

from agt_sea.config import AVAILABLE_MODELS, get_model_name
from agt_sea.models.state import LLMProvider

from components.labels import CREATIVE_PHILOSOPHY_LABELS, STRATEGIC_PHILOSOPHY_LABELS


# ---------------------------------------------------------------------------
# Sidebar renderer
# ---------------------------------------------------------------------------

def render_sidebar() -> None:
    """Render the sidebar: logo, global parameters, and footer.

    Writes to st.session_state keys:
        strategic_philosophy, creative_philosophy, cd_philosophy,
        llm_provider, llm_model, max_iterations, approval_threshold
    """
    # Logo is rendered via st.logo() in app.py, above the page nav.

    # --- Philosophy group ---
    selected_strategic_philosophy = st.sidebar.selectbox(
        "PHILOSOPHY: STRATEGY",
        options=list(STRATEGIC_PHILOSOPHY_LABELS.keys()),
        format_func=lambda x: STRATEGIC_PHILOSOPHY_LABELS[x],
        help="Sets the Strategist's approach and lens.",
    )
    st.session_state.strategic_philosophy = selected_strategic_philosophy

    selected_creative_philosophy = st.sidebar.selectbox(
        "PHILOSOPHY: CREATIVE",
        options=list(CREATIVE_PHILOSOPHY_LABELS.keys()),
        format_func=lambda x: CREATIVE_PHILOSOPHY_LABELS[x],
        help="Sets the Creative agent's generation lens.",
    )
    st.session_state.creative_philosophy = selected_creative_philosophy

    selected_cd_philosophy = st.sidebar.selectbox(
        "PHILOSOPHY: CD",
        options=list(CREATIVE_PHILOSOPHY_LABELS.keys()),
        format_func=lambda x: CREATIVE_PHILOSOPHY_LABELS[x],
        help="Sets the Creative Director's evaluation lens.",
    )
    st.session_state.cd_philosophy = selected_cd_philosophy

    st.sidebar.markdown("---")

    # --- LLM Provider (only providers with a valid API key) ---
    available_providers = [
        p for p in LLMProvider
        if os.environ.get(_api_key_name(p))
    ]
    if not available_providers:
        st.sidebar.warning("No API keys found. Set at least one in .env")
        available_providers = list(LLMProvider)

    selected_provider = st.sidebar.selectbox(
        "LLM PROVIDER",
        options=available_providers,
        format_func=lambda p: p.value,
        help="Only providers with a valid API key are selectable.",
    )
    st.session_state.llm_provider = selected_provider

    # --- LLM Model (dynamic based on provider) ---
    models = AVAILABLE_MODELS[selected_provider]
    default_model = get_model_name(selected_provider)
    default_index = models.index(default_model) if default_model in models else 0

    selected_model = st.sidebar.selectbox(
        "LLM MODEL",
        options=models,
        index=default_index,
        help="Available models for the selected provider.",
    )
    st.session_state.llm_model = selected_model

    st.sidebar.markdown("---")

    # --- Max Iterations ---
    max_iter = st.sidebar.number_input(
        "MAX ITERATIONS",
        min_value=1,
        max_value=5,
        value=3,
        help="Maximum creative loop iterations before forced exit.",
    )
    st.session_state.max_iterations = int(max_iter)

    # --- Approval Threshold ---
    threshold = st.sidebar.number_input(
        "APPROVAL THRESHOLD",
        min_value=0,
        max_value=100,
        value=80,
        help="Minimum CD score required for approval.",
    )
    st.session_state.approval_threshold = float(threshold)

    st.sidebar.markdown("---")

    # --- Footer ---
    st.sidebar.markdown(
        '<div class="footer-badge">SM λ ©</div>',
        unsafe_allow_html=True,
    )


def _api_key_name(provider: LLMProvider) -> str:
    """Return the environment variable name for a provider's API key."""
    return {
        LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
        LLMProvider.GOOGLE: "GOOGLE_API_KEY",
        LLMProvider.OPENAI: "OPENAI_API_KEY",
    }[provider]
