"""
agt_sea — Creative A Agent (Standard 2.0)

Territory generation. Takes the creative brief produced by the Strategist
and generates ``state.num_territories`` distinct creative territories —
tight artifacts with a title, a 1-2 sentence core idea, and a brief
rationale. No execution details, no channel recommendations — that's
the Creative B stage's job.

Structured output is enforced via a module-local ``TerritorySet`` wrapper
because LangChain's ``with_structured_output()`` rejects bare generic
aliases such as ``list[Territory]`` (raises ``ValueError: callable
list[...] is not supported by signature`` at composition time). The
wrapper is an implementation detail of this agent, not part of the
shared state contract, so it lives here rather than in ``models/state.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

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


class TerritorySet(BaseModel):
    """Structured-output wrapper around ``list[Territory]``.

    LangChain's ``with_structured_output()`` accepts a Pydantic class, a
    TypedDict, a JSON Schema dict, or a provider-specific tool schema —
    but not a generic alias like ``list[Territory]``. Wrapping the list
    in a Pydantic model gives a valid schema; the agent unwraps
    ``.territories`` before writing to state so the rest of the codebase
    never sees this wrapper.
    """

    territories: list[Territory] = Field(
        ...,
        description="The generated creative territories.",
    )


def _build_system_prompt(
    philosophy: CreativePhilosophy,
    provenance: Provenance,
    taste: Taste,
    num_territories: int,
) -> str:
    """Build the Creative A system prompt.

    Philosophy, provenance, and taste each follow the neutral-skip rule:
    when the value is NEUTRAL the corresponding section is omitted
    entirely and the prompt reads as if that feature wasn't there at
    all.

    ``num_territories`` is interpolated into the prompt so the agent
    asks for exactly the count the state requests (bounded 1-12 at the
    state layer via ``AgencyState.num_territories``).
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
Your role is to take a creative brief and generate {num_territories} distinct
creative territories. A territory is a tight artifact: a central creative
thought, nothing more. You are not writing executions, channel plans, or
campaign details at this stage — just the idea.

For each territory, provide:

1. **Title**: A short, evocative working name for the territory.

2. **Core Idea**: The central creative thought in 1-2 sentences. This is
   the big idea the whole campaign would ladder up to.

3. **Why It Works**: A brief rationale connecting the idea back to the
   insight and proposition in the creative brief.

Push for genuinely different directions. Each territory should be a
different strategic and creative angle on the brief — not variations on
a single theme. The first idea that comes to mind is usually the most
obvious; go past it. At least one territory should feel uncomfortable
or unexpected. Great creative work lives at the edge of what the client
expects."""


def _build_human_message(
    creative_brief: str,
    num_territories: int,
    rejection_context: str | None,
) -> str:
    """Build the Creative A human message.

    Neutral-skip on ``rejection_context``: when populated, an extra
    paragraph asks the agent to avoid the previously rejected direction;
    when ``None`` the message reads exactly as the no-rejection path.
    Rejection context is run-specific steering rather than a persistent
    lens, so it lives in the human turn rather than the system prompt.
    """
    rejection_paragraph = ""
    if rejection_context:
        rejection_paragraph = (
            "\n\nA previous batch of territories was rejected with this "
            f"feedback:\n\n{rejection_context}\n\n"
            "Avoid that direction and produce genuinely different territories."
        )

    return (
        f"Here is the creative brief:\n\n{creative_brief}\n\n"
        f"Please produce {num_territories} distinct creative territories."
        f"{rejection_paragraph}"
    )


def run_creative_a_st2(state: AgencyState) -> AgencyState:
    """Generate ``state.num_territories`` creative territories from the brief.

    Reads the creative brief plus the Creative A prompt-injection lenses
    (creative_a_st2_creative_philosophy, creative_a_st2_provenance,
    creative_a_st2_taste), the per-agent temperature
    (creative_a_st2_temperature), the territory count
    (num_territories), and the optional rerun feedback
    (territory_rejection_context). Writes the generated territories to
    ``state.territories`` and appends an ``AgentOutput`` to
    ``state.history``.

    Structured output: the underlying LLM call uses
    ``with_structured_output(TerritorySet)``; the returned wrapper is
    unwrapped to ``list[Territory]`` before writing to state.

    Args:
        state: The current agency state containing the creative brief
            and Creative A configuration.

    Returns:
        Updated state with populated ``territories`` and a new history
        entry.
    """
    provider = state.llm_provider or get_llm_provider()
    model = state.llm_model or get_model_name(provider)

    # Fetch the raw chat model so we can compose .with_structured_output()
    # on a BaseChatModel (the retry wrapper's RunnableRetry does not
    # expose that method). Wrap the composed runnable with transport
    # retries manually — same pattern as the Creative Director (ADR 0012).
    llm = get_llm(
        provider=provider,
        model=model,
        temperature=state.creative_a_st2_temperature,
        with_retry=False,
    )
    structured_llm = wrap_with_transport_retry(
        llm.with_structured_output(TerritorySet), provider
    )

    system_prompt = _build_system_prompt(
        philosophy=state.creative_a_st2_creative_philosophy,
        provenance=state.creative_a_st2_provenance,
        taste=state.creative_a_st2_taste,
        num_territories=state.num_territories,
    )
    human_content = _build_human_message(
        creative_brief=state.creative_brief or "",
        num_territories=state.num_territories,
        rejection_context=state.territory_rejection_context,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_content),
    ]

    result = invoke_with_validation_retry(structured_llm, messages)
    territories = result.territories

    # Plain-text rendering for the history entry so AgentOutput.content
    # stays consistent with other agents (all store a single string).
    # The typed territories remain on state.territories for programmatic
    # access.
    content_lines: list[str] = []
    for idx, territory in enumerate(territories, start=1):
        content_lines.append(f"Territory {idx}: {territory.title}")
        content_lines.append(f"Core idea: {territory.core_idea}")
        content_lines.append(f"Why it works: {territory.why_it_works}")
        content_lines.append("")
    content = "\n".join(content_lines).rstrip()

    state.territories = territories
    state.status = WorkflowStatus.IN_PROGRESS
    state.history.append(
        AgentOutput(
            agent=AgentRole.CREATIVE_A_ST2,
            provider=provider,
            model=model,
            iteration=state.iteration,
            content=content,
            timestamp=datetime.now(UTC),
        )
    )

    return state
