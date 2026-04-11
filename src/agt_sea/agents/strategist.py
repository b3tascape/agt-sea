"""
agt_sea — Strategist Agent

Takes a raw client brief and produces a structured creative brief
that will guide the Creative agent's idea generation.
"""

from __future__ import annotations

from datetime import UTC, datetime

from langchain_core.messages import SystemMessage, HumanMessage

from agt_sea.llm.provider import get_llm
from agt_sea.models.state import (
    AgencyState,
    AgentOutput,
    AgentRole,
    StrategicPhilosophy,
    WorkflowStatus,
)

from agt_sea.config import get_llm_provider, get_model_name
from agt_sea.prompts.loader import (
    load_guidance,
    load_strategic_philosophy,
    load_template,
)


def _build_system_prompt(philosophy: StrategicPhilosophy) -> str:
    """Build the strategist system prompt with injected philosophy, template, and guidance.

    When philosophy is NEUTRAL, no philosophy section is injected — the
    prompt reads as if the feature wasn't there at all.
    """
    template_text = load_template("creative_brief")
    proposition_guidance = load_guidance("proposition_101_lite")

    philosophy_section = ""
    if philosophy != StrategicPhilosophy.NEUTRAL:
        philosophy_text = load_strategic_philosophy(philosophy)
        philosophy_section = f"\nYour strategic philosophy:\n{philosophy_text}\n"

    return (
        "You are a senior brand strategist at a world-class creative agency "
        "renowned for its strategic excellence and award-winning creative output.\n"
        f"{philosophy_section}\n"
        "Your role is to take a raw client brief and transform it into a clear, "
        "actionable creative brief that will guide the creative team.\n\n"
        "Structure your creative brief using the following format:\n\n"
        f"{template_text}\n\n"
        "Replace each [Answer goes here] placeholder with your response. Replace "
        "[CREATIVE BRIEF TITLE] with a concise, descriptive title for the brief. "
        "Keep the section headings and overall structure intact. Note that the "
        "proposition should be bold (wrapped in ** markers) as indicated in the template.\n\n"
        "PROPOSITION WRITING GUIDANCE\n\n"
        "The single-minded proposition is the most important element of the brief. "
        "Use the following guidance when crafting it:\n\n"
        f"{proposition_guidance}\n\n"
        "Be concise and opinionated. A great creative brief is a springboard, not an "
        "essay. Take a clear point of view — the creative team needs direction, not "
        "options."
    )


def run_strategist(state: AgencyState) -> AgencyState:
    """Process the client brief and produce a creative brief.

    Args:
        state: The current agency state containing the client brief.

    Returns:
        Updated state with the creative brief and history entry.
    """
    provider = state.llm_provider or get_llm_provider()
    model = state.llm_model or get_model_name(provider)
    llm = get_llm(provider=provider, model=model)

    messages = [
        SystemMessage(content=_build_system_prompt(state.strategic_philosophy)),
        HumanMessage(content=(
            f"Here is the client brief:\n\n{state.client_brief}\n\n"
            "Please produce a creative brief."
        )),
    ]

    response = llm.invoke(messages)
    creative_brief = response.content

    # Update state
    state.creative_brief = creative_brief
    state.status = WorkflowStatus.IN_PROGRESS
    state.history.append(
        AgentOutput(
            agent=AgentRole.STRATEGIST,
            provider=provider,
            model=model,
            iteration=state.iteration,
            content=creative_brief,
            timestamp=datetime.now(UTC),
        )
    )

    return state