"""
agt_sea — Progress Component

Renders a live status container for a single graph node during
pipeline execution. Called once per node event in the streaming loop.

Per-node render shapes:

* Standard 1.0 — every node renders its full agent output. The
  streaming widgets ARE the audit trail until the run reaches the
  terminal UI.
* Standard 2.0 — strategist_st2 + creative_a_st2 + cd_grader_st2 render
  the same way; creative_b_st2 / cd_feedback_st2 / cd_synthesis_st2
  render compact previews (campaign title + deliverable names; first
  paragraph of the direction; score summary + comparison notes only).
  The full creative brief lives in a persistent expander on the
  Workflow v2 tab; the full agent outputs land in the pipeline history
  once the run terminates.
"""

from __future__ import annotations

from typing import Any

import streamlit as st


_NODE_LABELS: dict[str, tuple[str, str]] = {
    # --- Standard 1.0 ---
    "strategist_st1": ("strategist", "writing creative brief..."),
    "creative_st1": ("creative", "generating ideas..."),
    "creative_director_st1": ("creative director", "evaluating work..."),
    "check_iterations": ("iteration check", "checking iteration limit..."),
    "finalise_approved": ("approved", "creative work approved."),
    "finalise_max_iterations": ("max iterations", "selecting best work..."),
    # --- Standard 2.0 ---
    "strategist_st2": ("strategist", "writing creative brief..."),
    "creative_a_st2": ("creative a", "generating territories..."),
    "interrupt_territory_selection": (
        "territory selection",
        "awaiting user selection...",
    ),
    "creative_b_st2": ("creative b", "developing campaign..."),
    "cd_grader_st2": ("cd grader", "scoring campaign..."),
    "cd_feedback_st2": ("cd feedback", "writing revision direction..."),
    "cd_synthesis_st2": ("cd synthesis", "writing final recommendation..."),
    "finalise_failed": ("failed", "run failed."),
}


def _first_paragraph(text: str, max_chars: int = 50) -> str:
    """Return the first paragraph of ``text``, capped at ``max_chars``.

    Used by the v2 cd_feedback_st2 streaming preview — the full
    direction is in the pipeline history at the end; this just gives a
    teaser.
    """
    if not text:
        return ""
    head, _, _ = text.strip().partition("\n\n")
    head = head.strip()
    if len(head) > max_chars:
        head = head[:max_chars].rstrip() + "..."
    return head


def _field(obj: Any, name: str, default: Any = None) -> Any:
    """Read ``name`` off a possibly-Pydantic-or-dict streaming update.

    LangGraph stream updates may carry per-field values as Pydantic
    instances (when the agent set the field directly with a model) or
    as dicts (after rehydration). This helper covers both shapes
    without the call sites needing to branch every time.
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def render_node_progress(node_name: str, node_output: dict) -> None:
    """Render a status container for a single graph node event.

    Args:
        node_name: The graph node name (e.g. "strategist_st1",
            "creative_a_st2").
        node_output: The state update dict emitted by this node.
    """
    label, description = _NODE_LABELS.get(
        node_name, (node_name, "processing...")
    )

    with st.status(f"{label}", expanded=False) as status:
        st.write(description)

        # --- Standard 1.0 ---
        if node_name == "strategist_st1":
            st.markdown("**creative brief:**")
            st.markdown(node_output.get("creative_brief") or "")
            status.update(label=f"{label} ✓", state="complete")

        elif node_name == "creative_st1":
            iteration = node_output.get("iteration", 0)
            st.markdown(f"**iteration {iteration} — concepts:**")
            st.markdown(node_output.get("creative_concept") or "")
            status.update(
                label=f"{label} · iteration {iteration} ✓",
                state="complete",
            )

        elif node_name == "creative_director_st1":
            evaluation = node_output.get("cd_evaluation")
            if evaluation is not None:
                score = _field(evaluation, "score")
                strengths = _field(evaluation, "strengths") or []
                weaknesses = _field(evaluation, "weaknesses") or []
                direction = _field(evaluation, "direction") or ""
                if score is not None:
                    st.metric("score", f"{score}/100")
                if strengths:
                    st.markdown("**strengths:**")
                    for item in strengths:
                        st.markdown(f"- {item}")
                if weaknesses:
                    st.markdown("**weaknesses:**")
                    for item in weaknesses:
                        st.markdown(f"- {item}")
                if direction:
                    st.markdown(f"**direction:** {direction}")
            status.update(label=f"{label} ✓", state="complete")

        # --- Standard 2.0 ---
        elif node_name == "strategist_st2":
            st.markdown("**creative brief:**")
            st.markdown(node_output.get("creative_brief") or "")
            status.update(label=f"{label} ✓", state="complete")

        elif node_name == "creative_a_st2":
            # Titles only — full territory cards render below the
            # streaming widgets in the territory-selection UI.
            territories = node_output.get("territories") or []
            st.markdown(f"**{len(territories)} territories generated:**")
            for territory in territories:
                title = _field(territory, "title", "")
                st.markdown(f"- {title}")
            status.update(label=f"{label} ✓", state="complete")

        elif node_name == "interrupt_territory_selection":
            selected = node_output.get("selected_territory")
            if selected is not None:
                title = _field(selected, "title", "")
                st.markdown(f"**selected:** {title}")
                status.update(label=f"{label} ✓", state="complete")
            else:
                rejection = node_output.get("territory_rejection_context")
                if rejection:
                    st.markdown(
                        f"**rerun requested with context:** {rejection}"
                    )
                else:
                    st.markdown("**rerun requested** (no steering)")
                status.update(label=f"{label} · rerun", state="complete")

        elif node_name == "creative_b_st2":
            # Compact v2 preview: campaign title + deliverable names
            # only. Full CampaignConcept (core idea, deliverable
            # explanations, why-it-works) lands in the pipeline
            # history at terminal.
            iteration = node_output.get("iteration", 0)
            concept = node_output.get("campaign_concept")
            if concept is not None:
                title = _field(concept, "title", "")
                deliverables = _field(concept, "deliverables") or []
                if title:
                    st.markdown(
                        f"**iteration {iteration} — campaign:** {title}"
                    )
                if deliverables:
                    st.markdown("**deliverables:**")
                    for deliverable in deliverables:
                        d_name = _field(deliverable, "name", "")
                        st.markdown(f"- {d_name}")
            status.update(
                label=f"{label} · iteration {iteration} ✓",
                state="complete",
            )

        elif node_name == "cd_grader_st2":
            evaluation = node_output.get("grader_evaluation")
            if evaluation is not None:
                score = _field(evaluation, "score")
                rationale = _field(evaluation, "rationale", "")
                if score is not None:
                    st.metric("score", f"{score}/100")
                if rationale:
                    st.markdown(f"**rationale:** {rationale}")
            status.update(label=f"{label} ✓", state="complete")

        elif node_name == "cd_feedback_st2":
            # Compact v2 preview: direction summary (first paragraph,
            # capped). Full direction lands in the pipeline history.
            direction = node_output.get("cd_feedback_direction")
            if direction:
                st.markdown("**direction (summary):**")
                st.markdown(_first_paragraph(direction))
            status.update(label=f"{label} ✓", state="complete")

        elif node_name == "cd_synthesis_st2":
            # Compact v2 preview: score summary list + comparison
            # notes only. Selected title and recommendation narrative
            # live in the terminal UI's synthesis output and the
            # pipeline history.
            synthesis = node_output.get("cd_synthesis")
            if synthesis is not None:
                score_summary = _field(synthesis, "score_summary") or []
                comparison_notes = _field(synthesis, "comparison_notes")
                if score_summary:
                    st.markdown("**score summary:**")
                    for summary in score_summary:
                        s_title = _field(summary, "title", "")
                        s_score = _field(summary, "score")
                        s_assessment = _field(summary, "assessment", "")
                        score_label = (
                            f"{s_score}/100" if s_score is not None else ""
                        )
                        st.markdown(
                            f"- **{s_title}** ({score_label}) — "
                            f"{s_assessment}"
                        )
                if comparison_notes:
                    st.markdown("**comparison notes:**")
                    st.markdown(comparison_notes)
            status.update(label=f"{label} ✓", state="complete")

        # --- Finalisers + fallback ---
        elif node_name in (
            "finalise_approved",
            "finalise_max_iterations",
            "finalise_failed",
        ):
            status.update(label=f"{label}", state="complete")

        else:
            status.update(label=f"{label} ✓", state="complete")
