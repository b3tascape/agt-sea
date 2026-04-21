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

from components.labels import (
    CREATIVE_PHILOSOPHY_LABELS,
    PROVENANCE_LABELS,
    STRATEGIC_PHILOSOPHY_LABELS,
    TASTE_LABELS,
)


# ---------------------------------------------------------------------------
# Sidebar renderer
# ---------------------------------------------------------------------------

def render_sidebar() -> None:
    """Render the sidebar: logo, global parameters, and footer.

    Writes to st.session_state keys:
        strategic_philosophy, creative_philosophy, cd_philosophy,
        llm_provider, llm_model, max_iterations, approval_threshold.

        Standard 2.0 (inside the collapsible "STANDARD 2.0 CONTROLS"
        expander — unused by Standard 1.0):
            creative1_provenance, creative1_taste, creative1_temperature,
            creative2_provenance, creative2_taste, creative2_temperature,
            cd_provenance, cd_taste, cd_feedback_temperature,
            cd_synthesis_temperature.
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

    # --- Standard 2.0 controls (per-role provenance/taste + per-agent temperature) ---
    # All controls inside this expander are v2-specific — Standard 1.0 ignores
    # every field. Grouped behind a single collapsed expander so the sidebar
    # stays approachable for users only running the v1 workflow. Streamlit
    # does not allow nested expanders, so each role is a markdown sub-heading.
    with st.sidebar.expander("STANDARD 2.0 CONTROLS", expanded=False):
        st.markdown("**Creative 1** — territory generation")
        st.session_state.creative1_provenance = st.selectbox(
            "PROVENANCE: CREATIVE 1",
            options=list(PROVENANCE_LABELS.keys()),
            format_func=lambda x: PROVENANCE_LABELS[x],
            help="Background/upbringing lens injected into Creative 1.",
            key="sb_creative1_provenance",
        )
        st.session_state.creative1_taste = st.selectbox(
            "TASTE: CREATIVE 1",
            options=list(TASTE_LABELS.keys()),
            format_func=lambda x: TASTE_LABELS[x],
            help="Aesthetic/influence lens injected into Creative 1.",
            key="sb_creative1_taste",
        )
        st.session_state.creative1_temperature = st.slider(
            "TEMPERATURE: CREATIVE 1",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.05,
            help="Sampling temperature for Creative 1 (territory generation).",
            key="sb_creative1_temperature",
        )

        st.markdown("---")
        st.markdown("**Creative 2** — campaign development")
        st.session_state.creative2_provenance = st.selectbox(
            "PROVENANCE: CREATIVE 2",
            options=list(PROVENANCE_LABELS.keys()),
            format_func=lambda x: PROVENANCE_LABELS[x],
            help="Background/upbringing lens injected into Creative 2.",
            key="sb_creative2_provenance",
        )
        st.session_state.creative2_taste = st.selectbox(
            "TASTE: CREATIVE 2",
            options=list(TASTE_LABELS.keys()),
            format_func=lambda x: TASTE_LABELS[x],
            help="Aesthetic/influence lens injected into Creative 2.",
            key="sb_creative2_taste",
        )
        st.session_state.creative2_temperature = st.slider(
            "TEMPERATURE: CREATIVE 2",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.05,
            help="Sampling temperature for Creative 2 (campaign development).",
            key="sb_creative2_temperature",
        )

        st.markdown("---")
        st.markdown("**Creative Director** — feedback + synthesis")
        st.caption(
            "Provenance and taste are shared by CD Feedback and CD Synthesis. "
            "CD Grader is always neutral by contract."
        )
        st.session_state.cd_provenance = st.selectbox(
            "PROVENANCE: CD",
            options=list(PROVENANCE_LABELS.keys()),
            format_func=lambda x: PROVENANCE_LABELS[x],
            help="Background/upbringing lens for CD Feedback and CD Synthesis.",
            key="sb_cd_provenance",
        )
        st.session_state.cd_taste = st.selectbox(
            "TASTE: CD",
            options=list(TASTE_LABELS.keys()),
            format_func=lambda x: TASTE_LABELS[x],
            help="Aesthetic/influence lens for CD Feedback and CD Synthesis.",
            key="sb_cd_taste",
        )
        st.session_state.cd_feedback_temperature = st.slider(
            "TEMPERATURE: CD FEEDBACK",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.05,
            help="Sampling temperature for CD Feedback (qualitative revision direction).",
            key="sb_cd_feedback_temperature",
        )
        st.session_state.cd_synthesis_temperature = st.slider(
            "TEMPERATURE: CD SYNTHESIS",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.05,
            help="Sampling temperature for CD Synthesis (final editorial judgement).",
            key="sb_cd_synthesis_temperature",
        )

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
