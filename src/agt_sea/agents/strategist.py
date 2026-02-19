"""
agt_sea — Strategist Agent

Takes a raw client brief and produces a structured creative brief
that will guide the Creative agent's idea generation.
"""

from __future__ import annotations

from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage

from agt_sea.llm.provider import get_llm
from agt_sea.models.state import (
    AgencyState,
    AgentOutput,
    AgentRole,
    WorkflowStatus,
)

from agt_sea.config import get_llm_provider, get_model_name

STRATEGIST_SYSTEM_PROMPT = """You are a senior brand strategist at a world-class creative agency.

Your role is to take a raw client brief and transform it into a clear, 
actionable creative brief that will guide the creative team.

Your creative brief should include:

1. **Challenge**: What is the core problem or opportunity? Distil the client's 
   brief into a single, focused challenge statement.

2. **Audience**: Who are we talking to? Define the primary audience — their 
   mindset, motivations, and tensions relevant to this brief.

3. **Insight**: What is the human truth or cultural tension that this work 
   should tap into? This should feel surprising yet obvious.

4. **Proposition**: What is the single most compelling thing we can say or 
   demonstrate? One sentence maximum.

5. **Tone & Guardrails**: How should this work feel? What should it absolutely 
   not be?

Be concise and opinionated. A great creative brief is a springboard, not an 
essay. Take a clear point of view — the creative team needs direction, not 
options."""


def run_strategist(state: AgencyState) -> AgencyState:
    """Process the client brief and produce a creative brief.

    Args:
        state: The current agency state containing the client brief.

    Returns:
        Updated state with the creative brief and history entry.
    """
    llm = get_llm()
    provider = get_llm_provider()

    messages = [
        SystemMessage(content=STRATEGIST_SYSTEM_PROMPT),
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
            model=get_model_name(provider),
            content=creative_brief,
            timestamp=datetime.utcnow(),
        )
    )

    return state