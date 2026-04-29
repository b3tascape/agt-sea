"""
agt_sea — CD Synthesis Agent (Standard 2.0)

Final editorial judgement — the output the user sees at the end of the
Standard 2.0 pipeline. The Creative Director, standing behind the work,
presents the recommendation as a structured ``CDSynthesis``.

Schema built for N concepts even though the simplified v2 graph supplies
one. When exactly one campaign concept is passed in, ``comparison_notes``
must be ``None`` (see ``CDSynthesis``); when multiple are passed (future
parallel variant), the LLM should populate it.

Philosophy, provenance, and taste are injected via the neutral-skip
pattern. Temperature comes from ``state.cd_synthesis_st2_temperature``.

The system prompt was drafted for this phase (ADR 0014 marked it TBC).
Design intent: confident recommendation voice, explicit instruction to
skip comparison when only one concept is present, structured fields
line up with the user-facing component that will render this later.
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
    CDSynthesis,
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
    """Build the CD Synthesis system prompt.

    Philosophy, provenance, and taste each follow the neutral-skip rule.
    The prompt is explicit about the single-concept vs multi-concept
    branches so the LLM populates ``comparison_notes`` correctly.
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

    return f"""You are a Creative Director presenting the finished campaign work. This
is the output the user sees — polished, decisive, compelling. You are not
reviewing or critiquing: you are standing behind the work.
{philosophy_section}{provenance_section}{taste_section}
You have been given one or more campaign concepts, each with a grader
score, plus the iteration history that produced them. Produce a
structured ``CDSynthesis``:

1. **selected_title** — the title of the concept you recommend. When
   only one concept has been developed, recommend that one. When
   multiple have been developed, pick the strongest.

2. **recommendation** — a crafted narrative paragraph presenting the
   idea, explaining why it works, and making the case for it. This is
   the paragraph the client reads. Confident and clear, not defensive.

3. **score_summary** — one entry per concept (title, score, short
   editorial assessment). Always populated, even when there is only
   one concept.

4. **comparison_notes** — cross-concept commentary. Populate this ONLY
   when more than one concept was developed. When a single concept was
   developed, set it to null. Do not fabricate a comparison.

Your tone is that of a senior creative who believes in the work. The
recommendation should read as a presentation, not a review."""


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


def _render_grader_evaluation(grader: GraderEvaluation | None) -> str:
    """Render a grader evaluation for the human message, or a placeholder."""
    if grader is None:
        return "(no grader evaluation recorded for this concept)"
    return f"Score: {grader.score}/100\nRationale: {grader.rationale}"


def _render_history(state: AgencyState) -> str:
    """Render the iteration history as a compact log.

    The synthesis prompt benefits from seeing how the work evolved —
    particularly for revision runs where the graded concept is the last
    of several. A full dump of every agent's content would be too long;
    this helper emits a one-line-per-entry summary with iteration,
    agent, and the first ~120 characters of content.
    """
    if not state.history:
        return "(no history recorded)"
    lines: list[str] = []
    for entry in state.history:
        snippet = entry.content.replace("\n", " ").strip()
        if len(snippet) > 120:
            snippet = snippet[:117] + "..."
        lines.append(
            f"- iter {entry.iteration} [{entry.agent.value}]: {snippet}"
        )
    return "\n".join(lines)


def run_cd_synthesis_st2(state: AgencyState) -> AgencyState:
    """Produce the final editorial judgement on the campaign work.

    Simplified v2 graph: evaluates a single ``state.campaign_concept``
    and ``state.grader_evaluation``. Schema and prompt support N
    concepts for the future parallel variant — when only one is passed,
    the system prompt instructs the LLM to leave ``comparison_notes``
    as ``None``.

    Reads ``state.campaign_concept`` (required), ``state.grader_evaluation``
    (optional — rendered as a placeholder when absent), ``state.history``,
    and the CD injection lenses (``creative_director_st2_creative_philosophy``,
    ``creative_director_st2_provenance``, ``creative_director_st2_taste``).
    Temperature from ``state.cd_synthesis_st2_temperature``.

    Writes ``state.cd_synthesis`` and appends an ``AgentOutput`` to
    ``state.history``.

    Raises:
        ValueError: If ``state.campaign_concept`` is None. Synthesis has
            nothing to present without a finished campaign concept.
    """
    if state.campaign_concept is None:
        raise ValueError(
            "run_cd_synthesis_st2 requires state.campaign_concept to be set. "
            "The synthesis agent evaluates a finished campaign — Creative "
            "B must run first."
        )

    provider = state.llm_provider or get_llm_provider()
    model = state.llm_model or get_model_name(provider)

    # Raw chat model so we can compose .with_structured_output() before
    # wrapping with transport retry.
    llm = get_llm(
        provider=provider,
        model=model,
        temperature=state.cd_synthesis_st2_temperature,
        with_retry=False,
    )
    structured_llm = wrap_with_transport_retry(
        llm.with_structured_output(CDSynthesis), provider
    )

    system_prompt = _build_system_prompt(
        philosophy=state.creative_director_st2_creative_philosophy,
        provenance=state.creative_director_st2_provenance,
        taste=state.creative_director_st2_taste,
    )

    concept_block = _render_campaign_concept(state.campaign_concept)
    grader_block = _render_grader_evaluation(state.grader_evaluation)
    history_block = _render_history(state)

    human_content = (
        f"Here is the creative brief:\n\n{state.creative_brief}\n\n"
        f"Here is the finished campaign concept (one concept total):\n\n"
        f"{concept_block}\n\n"
        f"Grader evaluation for this concept:\n\n{grader_block}\n\n"
        f"Iteration history:\n\n{history_block}\n\n"
        "Produce the final CDSynthesis. Since only one concept was "
        "developed, leave `comparison_notes` as null."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_content),
    ]

    synthesis = invoke_with_validation_retry(structured_llm, messages)

    state.cd_synthesis = synthesis
    state.status = WorkflowStatus.REVIEW
    state.history.append(
        AgentOutput(
            agent=AgentRole.CD_SYNTHESIS_ST2,
            provider=provider,
            model=model,
            iteration=state.iteration,
            content=(
                f"Recommendation: {synthesis.selected_title}\n\n"
                f"{synthesis.recommendation}"
            ),
            timestamp=datetime.now(UTC),
        )
    )

    return state
