"""
agt_sea — CD Grader Agent (Standard 2.0)

Scoring-only evaluation of a campaign concept against the creative brief.
Deliberately narrow by contract:

* **No philosophy, provenance, or taste injection.** The grader is
  built for repeatability — the same concept should score the same way
  regardless of which creative lens the rest of the graph is running.
* **Temperature comes from ``state.grader_temperature``** (default 0.0,
  hardcoded at the state layer — not sidebar-exposed). Kept on state
  rather than hardcoded in the agent so the recorded run metadata
  matches the actual LLM call exactly.
* **Lean output schema:** just ``score`` and ``rationale`` on
  ``GraderEvaluation`` — no strengths/weaknesses/direction. Feedback is
  the CD Feedback agent's job; synthesis is CD Synthesis's.

The system prompt was drafted for this phase (ADR 0014 marked it TBC).
Design intent: unambiguous banding, objectivity language, explicit "no
coaching" instruction to keep the grader out of CD Feedback's lane.
"""

from __future__ import annotations

from datetime import UTC, datetime

from langchain_core.messages import HumanMessage, SystemMessage

from agt_sea.config import get_llm_provider, get_model_name
from agt_sea.llm.provider import (
    get_llm,
    invoke_with_validation_retry,
    wrap_with_transport_retry,
)
from agt_sea.models.state import (
    AgencyState,
    AgentOutput,
    AgentRole,
    CampaignConcept,
    GraderEvaluation,
    WorkflowStatus,
)


def _build_system_prompt() -> str:
    """Build the CD Grader system prompt.

    No parameters: the grader is neutral by contract — no philosophy,
    provenance, or taste. The prompt is fixed.
    """
    return """You are a scoring rubric for a creative campaign concept. Your only job
is to produce a numeric score out of 100 and a brief rationale justifying
it.

You are not a creative collaborator. You do not offer direction, coaching,
or opinion. You do not critique taste. You score objectively against the
creative brief: does the campaign concept answer the brief, is the core
idea original, is the execution specific, does it connect to the stated
insight?

Scoring bands:
- 90-100: Exceptional. On-strategy, genuinely original, specific execution.
- 80-89: Strong. On-strategy with minor gaps in originality or specificity.
- 60-79: Promising but significantly underdeveloped.
- 40-59: Off-strategy or derivative. Needs a fundamental rethink.
- Below 40: Does not answer the brief.

Be consistent. The same concept must receive the same score on
re-evaluation. A short rationale (1-3 sentences) justifies the score —
that's all the prose required. Do not offer revision direction. Do not
praise or encourage."""


def _render_campaign_concept(concept: CampaignConcept) -> str:
    """Render a CampaignConcept as a readable block for the human message."""
    deliverables = "\n".join(
        f"- {d.name}: {d.explanation}" for d in concept.deliverables
    )
    return (
        f"Title: {concept.title}\n"
        f"Core idea: {concept.core_idea}\n"
        f"Deliverables:\n{deliverables}\n"
        f"Why it works: {concept.why_it_works}"
    )


def run_cd_grader(state: AgencyState) -> AgencyState:
    """Score the current campaign concept out of 100 against the brief.

    Reads ``state.campaign_concept`` (required) and ``state.creative_brief``.
    Writes ``state.grader_evaluation`` and appends an ``AgentOutput`` to
    ``state.history``. Temperature comes from ``state.grader_temperature``.

    Raises:
        ValueError: If ``state.campaign_concept`` is None. The grader has
            nothing to score without a campaign concept — caller contract
            violation, surfaced before any LLM call.
    """
    if state.campaign_concept is None:
        raise ValueError(
            "run_cd_grader requires state.campaign_concept to be set. "
            "Creative 2 must run before the grader."
        )

    provider = state.llm_provider or get_llm_provider()
    model = state.llm_model or get_model_name(provider)

    # Raw chat model so we can compose .with_structured_output() before
    # wrapping with transport retry — same pattern as Creative 2 and CD.
    llm = get_llm(
        provider=provider,
        model=model,
        temperature=state.grader_temperature,
        with_retry=False,
    )
    structured_llm = wrap_with_transport_retry(
        llm.with_structured_output(GraderEvaluation), provider
    )

    messages = [
        SystemMessage(content=_build_system_prompt()),
        HumanMessage(
            content=(
                f"Here is the creative brief:\n\n{state.creative_brief}\n\n"
                f"Here is the campaign concept to score (iteration "
                f"{state.iteration}):\n\n"
                f"{_render_campaign_concept(state.campaign_concept)}\n\n"
                "Return a score out of 100 and a short rationale."
            )
        ),
    ]

    evaluation = invoke_with_validation_retry(structured_llm, messages)

    state.grader_evaluation = evaluation
    state.status = WorkflowStatus.REVIEW
    state.history.append(
        AgentOutput(
            agent=AgentRole.CD_GRADER,
            provider=provider,
            model=model,
            iteration=state.iteration,
            content=(
                f"Score: {evaluation.score}/100\n"
                f"Rationale: {evaluation.rationale}"
            ),
            timestamp=datetime.now(UTC),
        )
    )

    return state
