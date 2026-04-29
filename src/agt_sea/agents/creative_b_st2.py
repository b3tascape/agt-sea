"""
agt_sea — Creative B Agent (Standard 2.0)

Campaign development. Takes the territory the user selected at the
interrupt and develops it into a full ``CampaignConcept`` — title, core
idea, deliverables, and rationale — enforced via
``with_structured_output(CampaignConcept)``.

Two prompt paths, mirroring the Standard 1.0 Creative agent:

* **Initial** — works from the creative brief and the selected territory.
* **Revision** — fires when both ``state.grader_evaluation`` and
  ``state.cd_feedback_direction`` are populated, incorporating the
  grader's score and the CD's coaching into the next pass.

Philosophy, provenance, and taste are each injected via the neutral-skip
pattern. Temperature comes from ``state.creative_b_st2_temperature``.
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
    CreativePhilosophy,
    Provenance,
    Taste,
    Territory,
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
    """Build the Creative 2 initial system prompt.

    Philosophy, provenance, and taste each follow the neutral-skip rule:
    when the value is NEUTRAL the corresponding section is omitted
    entirely and the prompt reads as if that feature wasn't there at
    all.
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

    return f"""You are a senior creative at a world-class creative agency.
{philosophy_section}{provenance_section}{taste_section}
Your role is to take a selected creative territory and develop it into a
full campaign concept. The territory is the central creative thought —
your job is to deepen it into a campaign that could actually run.

Produce a structured ``CampaignConcept`` with:

1. **Title**: A punchy campaign title that lives with the idea.

2. **Core Idea**: The central creative thought in 1-2 sentences, carried
   forward from the selected territory but sharpened if it needs to be.

3. **Deliverables**: Concrete executions across channels and formats.
   Each deliverable is a name plus an explanation of how it brings the
   core idea to life. Be specific — actual content, actual formats,
   actual moments. Not vague platitudes. Pick a channel mix that suits
   the idea, unless the brief specifies otherwise.

4. **Why It Works**: Rationale connecting the campaign back to the
   insight and proposition in the creative brief.

Stay close to the selected territory's central thought. This is a
deepening step, not a second round of divergent thinking — don't pivot
to a new idea."""


def _build_revision_prompt(
    philosophy: CreativePhilosophy,
    provenance: Provenance,
    taste: Taste,
) -> str:
    """Build the Creative 2 revision system prompt.

    Same neutral-skip rule for all three injection lenses. Used when a
    previous campaign concept has been graded and coached, and Creative
    2 is being asked to iterate.
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

    return f"""You are a senior creative at a world-class creative agency.
{philosophy_section}{provenance_section}{taste_section}
You previously developed a campaign concept from a selected creative
territory. The work has been graded and you have received coaching from
the Creative Director. Use both to produce an improved campaign.

You should:
- Hold on to what's working in the current version
- Address the grader's critique head-on, not around the edges
- Follow the CD's direction — that's the whole point of the next pass
- Keep the campaign anchored to the original selected territory; this
  is a refinement, not a new idea

Produce a structured ``CampaignConcept``:

1. **Title**
2. **Core Idea** — 1-2 sentences
3. **Deliverables** — name + explanation per deliverable, specific and
   tangible
4. **Why It Works** — how this version delivers on the brief and
   addresses the CD's direction"""


def _render_territory(territory: Territory) -> str:
    """Render a Territory as a readable block for the human message."""
    return (
        f"Title: {territory.title}\n"
        f"Core idea: {territory.core_idea}\n"
        f"Why it works: {territory.why_it_works}"
    )


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


def run_creative_b_st2(state: AgencyState) -> AgencyState:
    """Develop the selected territory into a full campaign concept.

    On the initial pass, works from the creative brief plus the selected
    territory alone. On revision passes (``grader_evaluation`` and
    ``cd_feedback_direction`` both populated), incorporates the grader's
    score and the CD's coaching.

    Reads ``state.selected_territory`` (required), ``state.creative_brief``,
    the Creative B injection lenses (``creative_b_st2_creative_philosophy``,
    ``creative_b_st2_provenance``, ``creative_b_st2_taste``), the per-agent
    temperature (``creative_b_st2_temperature``), and the optional revision
    inputs (``grader_evaluation``, ``cd_feedback_direction``,
    ``campaign_concept``).

    Writes ``state.campaign_concept`` and appends an ``AgentOutput`` to
    ``state.history``.

    Raises:
        ValueError: If ``state.selected_territory`` is None. Creative B
            cannot run without a territory to develop — this is a caller
            contract violation, not a recoverable runtime condition, so
            it short-circuits with a clear error before any LLM call.
    """
    if state.selected_territory is None:
        raise ValueError(
            "run_creative_b_st2 requires state.selected_territory to be set. "
            "The graph's territory-selection interrupt (or a standalone "
            "caller) must populate it before invoking Creative B."
        )

    provider = state.llm_provider or get_llm_provider()
    model = state.llm_model or get_model_name(provider)

    # Raw chat model so we can compose .with_structured_output() before
    # wrapping with transport retry — same pattern as Creative A / CD.
    llm = get_llm(
        provider=provider,
        model=model,
        temperature=state.creative_b_st2_temperature,
        with_retry=False,
    )
    structured_llm = wrap_with_transport_retry(
        llm.with_structured_output(CampaignConcept), provider
    )

    is_revision = (
        state.grader_evaluation is not None
        and state.cd_feedback_direction is not None
    )

    if is_revision:
        system_prompt = _build_revision_prompt(
            philosophy=state.creative_b_st2_creative_philosophy,
            provenance=state.creative_b_st2_provenance,
            taste=state.creative_b_st2_taste,
        )
        previous_concept_block = (
            _render_campaign_concept(state.campaign_concept)
            if state.campaign_concept is not None
            else "(no prior campaign concept recorded)"
        )
        human_content = (
            f"Here is the creative brief:\n\n{state.creative_brief}\n\n"
            f"Here is the selected territory you are developing:\n\n"
            f"{_render_territory(state.selected_territory)}\n\n"
            f"Here is your previous campaign concept:\n\n"
            f"{previous_concept_block}\n\n"
            f"Here is the grader's score and rationale:\n\n"
            f"Score: {state.grader_evaluation.score}/100\n"
            f"Rationale: {state.grader_evaluation.rationale}\n\n"
            f"Here is the Creative Director's direction:\n\n"
            f"{state.cd_feedback_direction}\n\n"
            "Produce an improved campaign concept."
        )
    else:
        system_prompt = _build_system_prompt(
            philosophy=state.creative_b_st2_creative_philosophy,
            provenance=state.creative_b_st2_provenance,
            taste=state.creative_b_st2_taste,
        )
        human_content = (
            f"Here is the creative brief:\n\n{state.creative_brief}\n\n"
            f"Here is the selected territory you are developing:\n\n"
            f"{_render_territory(state.selected_territory)}\n\n"
            "Develop this territory into a full campaign concept."
        )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_content),
    ]

    campaign_concept = invoke_with_validation_retry(structured_llm, messages)

    # Plain-text rendering for AgentOutput.content so history display stays
    # consistent across agents (all store a single string). The typed
    # CampaignConcept remains on state.campaign_concept for programmatic
    # access and downstream agents.
    content = _render_campaign_concept(campaign_concept)

    state.campaign_concept = campaign_concept
    state.iteration += 1
    state.status = WorkflowStatus.REVIEW
    state.history.append(
        AgentOutput(
            agent=AgentRole.CREATIVE_B_ST2,
            provider=provider,
            model=model,
            iteration=state.iteration,
            content=content,
            timestamp=datetime.now(UTC),
        )
    )

    return state
