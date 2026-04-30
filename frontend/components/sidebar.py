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
        llm_provider, llm_model, max_iterations, approval_threshold.

        Standard 1.0 (inside the collapsible "WORKFLOW_ST1 CONTROLS"
        expander):
            strategist_st1_strategic_philosophy,
            creative_st1_creative_philosophy,
            creative_director_st1_creative_philosophy.

        Standard 2.0 (inside the collapsible "WORKFLOW_ST2 CONTROLS"
        expander):
            strategist_st2_strategic_philosophy,
            creative_a_st2_creative_philosophy,
            creative_a_st2_provenance, creative_a_st2_taste,
            creative_a_st2_temperature,
            creative_b_st2_creative_philosophy,
            creative_b_st2_provenance, creative_b_st2_taste,
            creative_b_st2_temperature,
            creative_director_st2_creative_philosophy,
            creative_director_st2_provenance,
            creative_director_st2_taste,
            cd_feedback_st2_temperature, cd_synthesis_st2_temperature.
    """
    # Logo is rendered via st.logo() in app.py, above the page nav.

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

    # --- Standard 1.0 controls (per-agent philosophies) ---
    # Streamlit does not allow nested expanders, so each agent is a markdown
    # sub-heading inside the expander.
    with st.sidebar.expander("WORKFLOW_ST1 CONTROLS", expanded=False):
        st.markdown("**Strategist**")
        st.session_state.strategist_st1_strategic_philosophy = st.selectbox(
            "STRATEGIC PHILOSOPHY",
            options=list(STRATEGIC_PHILOSOPHY_LABELS.keys()),
            format_func=lambda x: STRATEGIC_PHILOSOPHY_LABELS[x],
            help="Strategic lens for the Standard 1.0 Strategist.",
            key="sb_strategist_st1_strategic_philosophy",
        )

        st.markdown("---")
        st.markdown("**Creative**")
        st.session_state.creative_st1_creative_philosophy = st.selectbox(
            "CREATIVE PHILOSOPHY",
            options=list(CREATIVE_PHILOSOPHY_LABELS.keys()),
            format_func=lambda x: CREATIVE_PHILOSOPHY_LABELS[x],
            help="Creative lens for the Standard 1.0 Creative agent.",
            key="sb_creative_st1_creative_philosophy",
        )

        st.markdown("---")
        st.markdown("**Creative Director**")
        st.session_state.creative_director_st1_creative_philosophy = st.selectbox(
            "CREATIVE PHILOSOPHY",
            options=list(CREATIVE_PHILOSOPHY_LABELS.keys()),
            format_func=lambda x: CREATIVE_PHILOSOPHY_LABELS[x],
            help="Creative lens for the Standard 1.0 Creative Director.",
            key="sb_creative_director_st1_creative_philosophy",
        )

    # --- Standard 2.0 controls (per-agent philosophies + per-role
    # provenance/taste + per-agent temperature) ---
    with st.sidebar.expander("WORKFLOW_ST2 CONTROLS", expanded=False):
        st.markdown("**Strategist**")
        st.session_state.strategist_st2_strategic_philosophy = st.selectbox(
            "STRATEGIC PHILOSOPHY",
            options=list(STRATEGIC_PHILOSOPHY_LABELS.keys()),
            format_func=lambda x: STRATEGIC_PHILOSOPHY_LABELS[x],
            help="Strategic lens for the Standard 2.0 Strategist.",
            key="sb_strategist_st2_strategic_philosophy",
        )

        st.markdown("---")
        st.markdown("**Creative A** — territory generation")
        st.session_state.creative_a_st2_creative_philosophy = st.selectbox(
            "CREATIVE PHILOSOPHY",
            options=list(CREATIVE_PHILOSOPHY_LABELS.keys()),
            format_func=lambda x: CREATIVE_PHILOSOPHY_LABELS[x],
            help="Creative lens for Creative A (territory generation).",
            key="sb_creative_a_st2_creative_philosophy",
        )
        st.session_state.creative_a_st2_provenance = st.selectbox(
            "PROVENANCE",
            options=list(PROVENANCE_LABELS.keys()),
            format_func=lambda x: PROVENANCE_LABELS[x],
            help="Background/upbringing lens injected into Creative A.",
            key="sb_creative_a_st2_provenance",
        )
        st.session_state.creative_a_st2_taste = st.selectbox(
            "TASTE",
            options=list(TASTE_LABELS.keys()),
            format_func=lambda x: TASTE_LABELS[x],
            help="Aesthetic/influence lens injected into Creative A.",
            key="sb_creative_a_st2_taste",
        )
        st.session_state.creative_a_st2_temperature = st.slider(
            "TEMPERATURE",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.05,
            help="Sampling temperature for Creative A (territory generation).",
            key="sb_creative_a_st2_temperature",
        )

        st.markdown("---")
        st.markdown("**Creative B** — campaign development")
        st.session_state.creative_b_st2_creative_philosophy = st.selectbox(
            "CREATIVE PHILOSOPHY",
            options=list(CREATIVE_PHILOSOPHY_LABELS.keys()),
            format_func=lambda x: CREATIVE_PHILOSOPHY_LABELS[x],
            help="Creative lens for Creative B (campaign development).",
            key="sb_creative_b_st2_creative_philosophy",
        )
        st.session_state.creative_b_st2_provenance = st.selectbox(
            "PROVENANCE",
            options=list(PROVENANCE_LABELS.keys()),
            format_func=lambda x: PROVENANCE_LABELS[x],
            help="Background/upbringing lens injected into Creative B.",
            key="sb_creative_b_st2_provenance",
        )
        st.session_state.creative_b_st2_taste = st.selectbox(
            "TASTE",
            options=list(TASTE_LABELS.keys()),
            format_func=lambda x: TASTE_LABELS[x],
            help="Aesthetic/influence lens injected into Creative B.",
            key="sb_creative_b_st2_taste",
        )
        st.session_state.creative_b_st2_temperature = st.slider(
            "TEMPERATURE",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.05,
            help="Sampling temperature for Creative B (campaign development).",
            key="sb_creative_b_st2_temperature",
        )

        st.markdown("---")
        st.markdown("**Creative Director** — feedback + synthesis")
        st.caption(
            "Philosophy, provenance, and taste are shared by CD Feedback "
            "and CD Synthesis. CD Grader is always neutral by contract."
        )
        st.session_state.creative_director_st2_creative_philosophy = st.selectbox(
            "CREATIVE PHILOSOPHY",
            options=list(CREATIVE_PHILOSOPHY_LABELS.keys()),
            format_func=lambda x: CREATIVE_PHILOSOPHY_LABELS[x],
            help="Creative lens shared by CD Feedback and CD Synthesis.",
            key="sb_creative_director_st2_creative_philosophy",
        )
        st.session_state.creative_director_st2_provenance = st.selectbox(
            "PROVENANCE",
            options=list(PROVENANCE_LABELS.keys()),
            format_func=lambda x: PROVENANCE_LABELS[x],
            help="Background/upbringing lens for CD Feedback and CD Synthesis.",
            key="sb_creative_director_st2_provenance",
        )
        st.session_state.creative_director_st2_taste = st.selectbox(
            "TASTE",
            options=list(TASTE_LABELS.keys()),
            format_func=lambda x: TASTE_LABELS[x],
            help="Aesthetic/influence lens for CD Feedback and CD Synthesis.",
            key="sb_creative_director_st2_taste",
        )
        st.session_state.cd_feedback_st2_temperature = st.slider(
            "TEMPERATURE: CD FEEDBACK",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.05,
            help="Sampling temperature for CD Feedback (qualitative revision direction).",
            key="sb_cd_feedback_st2_temperature",
        )
        st.session_state.cd_synthesis_st2_temperature = st.slider(
            "TEMPERATURE: CD SYNTHESIS",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.05,
            help="Sampling temperature for CD Synthesis (final editorial judgement).",
            key="sb_cd_synthesis_st2_temperature",
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
