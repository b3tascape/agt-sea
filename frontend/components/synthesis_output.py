"""
agt_sea — Synthesis Output Component

Renders the CDSynthesis — the final user-facing editorial judgement at
the end of the Standard 2.0 pipeline — followed by the underlying
CampaignConcept. Title and recommendation narrative up top, per-concept
score summaries below, optional comparison notes when populated
(`comparison_notes` is None when only one concept was developed, which
is the simplified v2 graph's current case).

Pure display: accepts a CDSynthesis plus an optional CampaignConcept
and renders them. The component does not read from or write to
``st.session_state``.
"""

from __future__ import annotations

import streamlit as st

from agt_sea.models.state import CampaignConcept, CDSynthesis


def render_synthesis_output(
    synthesis: CDSynthesis,
    campaign: CampaignConcept | None = None,
) -> None:
    """Render the final synthesis followed by the campaign concept.

    Args:
        synthesis: The structured CD Synthesis recommendation.
        campaign: The CampaignConcept that was graded and synthesised.
            Rendered inside a collapsed expander so the synthesis
            narrative stays the primary read.
    """
    st.markdown("### final recommendation")
    st.markdown(f"#### {synthesis.selected_title}")
    st.markdown(synthesis.recommendation)

    if synthesis.score_summary:
        st.markdown("#### score summary")
        for summary in synthesis.score_summary:
            with st.container(border=True):
                col_score, col_detail = st.columns([1, 4])
                col_score.metric("score", f"{summary.score}/100")
                col_detail.markdown(f"**{summary.title}**")
                col_detail.markdown(summary.assessment)

    if synthesis.comparison_notes:
        st.markdown("#### comparison notes")
        st.markdown(synthesis.comparison_notes)

    if campaign is not None:
        st.markdown("---")
        with st.expander("campaign concept", expanded=False):
            _render_campaign_concept(campaign)


def _render_campaign_concept(campaign: CampaignConcept) -> None:
    """Render a CampaignConcept as a structured block."""
    st.markdown(f"#### {campaign.title}")
    st.markdown(
        "<p class='territory-label'>CORE IDEA</p>",
        unsafe_allow_html=True,
    )
    st.markdown(campaign.core_idea)

    if campaign.deliverables:
        st.markdown(
            "<p class='territory-label'>DELIVERABLES</p>",
            unsafe_allow_html=True,
        )
        for deliverable in campaign.deliverables:
            st.markdown(
                f"- **{deliverable.name}** — {deliverable.explanation}"
            )

    st.markdown(
        "<p class='territory-label'>WHY IT WORKS</p>",
        unsafe_allow_html=True,
    )
    st.markdown(campaign.why_it_works)
