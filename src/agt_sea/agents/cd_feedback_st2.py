"""
agt_sea — CD Feedback Agent (Standard 2.0)

Produces directional coaching on a campaign concept — the qualitative
revision direction that creative_2 reads on its next iteration.

CD Feedback operates on campaign concepts only.

Deliberate non-goals:

* **Does not score.** The grader owns scoring. Feedback is coaching.
* **Does not assume graph context.** The agent doesn't know or care
  whether the grader flagged the work as below threshold, whether
  iterations remain, or whether the graph will loop. It produces the
  best direction it can from the artifact it's been handed; the graph
  decides what happens next.
* **No imposed output format.** The model picks prose, bullets, or a
  mix — whichever conveys the direction most clearly.

Output is a free-text ``str`` written to ``state.cd_feedback_direction``
(the field Creative B reads on its revision path).

The system prompt was drafted for this phase (ADR 0014 marked it TBC).
"""

from __future__ import annotations

from datetime import UTC, datetime

from langchain_core.messages import HumanMessage, SystemMessage

from agt_sea.config import get_llm_provider, get_model_name
from agt_sea.llm.provider import get_llm
from agt_sea.models.state import (
    AgencyState,
    AgentOutput,
    AgentRole,
    CampaignConcept,
    CreativePhilosophy,
    GraderEvaluation,
    Provenance,
    Taste,
    WorkflowStatus,
)
from agt_sea.prompts.loader import (
    load_creative_philosophy,
    load_provenance,
    load_taste,
)


def _build_system_prompt(
    philosophy: CreativePhilosophy,
    provenance: Provenance,
    taste: Taste,
) -> str:
    """Build the CD Feedback system prompt.

    Philosophy, provenance, and taste each follow the neutral-skip rule:
    NEUTRAL omits the corresponding section entirely.

    The prompt does not reference the grader's threshold or the graph's
    iteration policy — feedback is produced on whatever artifact is
    supplied, and the graph decides whether to loop.
    """
    philosophy_section = ""
    if philosophy != CreativePhilosophy.NEUTRAL:
        philosophy_text = load_creative_philosophy(philosophy)
        philosophy_section = f"\nYour creative philosophy:\n{philosophy_text}\n"

    provenance_section = ""
    if provenance != Provenance.NEUTRAL:
        provenance_text = load_provenance(provenance)
        provenance_section = f"\nYour creative provenance:\n{provenance_text}\n"

    taste_section = ""
    if taste != Taste.NEUTRAL:
        taste_text = load_taste(taste)
        taste_section = f"\nYour creative taste:\n{taste_text}\n"

    return f"""You are a Creative Director giving directional notes on a campaign
concept in progress.
{philosophy_section}{provenance_section}{taste_section}
Your job is to produce actionable creative direction for the next pass.
You are not grading or scoring — another role owns that. You are not
deciding what happens next — the workflow handles that. Your output is
coaching.

Use everything you have been given: the creative brief, the campaign
concept, and any grader score and rationale that accompanies it. Do not
duplicate the grader's assessment — build on it. Do not assign a
numeric score.

Write directional coaching that is actionable and specific. Prose,
bullets, or a mix — use whatever format best conveys the feedback
clearly. The quality and precision of the direction matters, not the
format.

Be specific. \"Make it bolder\" is not direction. \"The core idea is too
literal — push the metaphor into the unexpected, and carry it through
the deliverables\" is direction."""


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


def _build_human_message(
    creative_brief: str | None,
    campaign_concept: CampaignConcept,
    grader_evaluation: GraderEvaluation | None,
) -> str:
    """Build the human message.

    Grader score/rationale is included when present but optional — the
    agent must be able to produce direction on a campaign concept even
    without a prior grade (e.g. pre-grader standalone use, or if a
    caller deliberately skipped the grader).
    """
    grader_block = ""
    if grader_evaluation is not None:
        grader_block = (
            f"\n\nThe grader scored this concept {grader_evaluation.score}/100. "
            f"Their rationale:\n\n{grader_evaluation.rationale}"
        )

    return (
        f"Here is the creative brief:\n\n{creative_brief}\n\n"
        f"Here is the current campaign concept:\n\n"
        f"{_render_campaign_concept(campaign_concept)}"
        f"{grader_block}\n\n"
        "Produce directional coaching for the next iteration."
    )


def run_cd_feedback_st2(state: AgencyState) -> AgencyState:
    """Produce directional coaching on the current campaign concept.

    Reads ``state.campaign_concept`` (required), ``state.creative_brief``,
    ``state.grader_evaluation`` (optional — rendered when present), the
    CD injection lenses (``creative_director_st2_creative_philosophy``,
    ``creative_director_st2_provenance``, ``creative_director_st2_taste``),
    and ``cd_feedback_st2_temperature``.

    Writes free-text coaching to ``state.cd_feedback_direction`` and
    appends an ``AgentOutput`` to ``state.history``.

    Output is free-text (``str``) rather than a structured model — the
    direction itself is the product. Uses ``llm.invoke(...).content``
    directly; no structured output, no validation retry.

    Raises:
        ValueError: If ``state.campaign_concept`` is None. CD Feedback
            operates on a campaign concept — caller contract violation,
            surfaced before any LLM call.
    """
    if state.campaign_concept is None:
        raise ValueError(
            "run_cd_feedback_st2 requires state.campaign_concept to be set."
        )

    provider = state.llm_provider or get_llm_provider()
    model = state.llm_model or get_model_name(provider)

    # Free-text output — plain get_llm with transport retry is enough.
    # No structured output composition, so with_retry=True is fine.
    llm = get_llm(
        provider=provider,
        model=model,
        temperature=state.cd_feedback_st2_temperature,
    )

    system_prompt = _build_system_prompt(
        philosophy=state.creative_director_st2_creative_philosophy,
        provenance=state.creative_director_st2_provenance,
        taste=state.creative_director_st2_taste,
    )
    human_content = _build_human_message(
        creative_brief=state.creative_brief,
        campaign_concept=state.campaign_concept,
        grader_evaluation=state.grader_evaluation,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_content),
    ]

    response = llm.invoke(messages)
    direction = response.content

    state.cd_feedback_direction = direction
    state.status = WorkflowStatus.REVIEW
    state.history.append(
        AgentOutput(
            agent=AgentRole.CD_FEEDBACK_ST2,
            provider=provider,
            model=model,
            iteration=state.iteration,
            content=direction,
            timestamp=datetime.now(UTC),
        )
    )

    return state
