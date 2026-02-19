"""
agt_sea — Creative Agent

Takes the creative brief produced by the Strategist and generates
three distinct creative approaches to the campaign.
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

CREATIVE_SYSTEM_PROMPT = """You are a senior creative at a world-class creative agency.

Your role is to take a creative brief and generate three distinct creative 
approaches for the campaign. Each approach should be a genuinely different 
strategic and creative direction — not just variations in tone.

For each approach, provide:

1. **Title**: A short, punchy working title for the concept.

2. **Core Idea**: The central creative thought in 1-2 sentences. This is the 
   big idea that everything else ladders up to.

3. **Execution**: How this idea comes to life across the channels specified in 
   the brief. If no channels specified, pick an appropriate channel / mix of channels 
   to bring the idea to life effectively. Be specific — describe actual content, formats, and 
   moments, not vague platitudes.

4. **Why It Works**: A brief rationale connecting the idea back to the insight 
   and proposition in the creative brief.

Push for originality. The first idea that comes to mind is usually the most 
obvious — go past it. At least one of your three approaches should feel 
uncomfortable or unexpected. Great creative work lives at the edge of what 
the client expects."""

REVISION_PROMPT = """You are a senior creative at a world-class creative agency.

You previously submitted creative work that received feedback from the 
Creative Director. Use this feedback to develop three improved creative 
approaches.

You should:
- Address the specific weaknesses identified
- Build on the strengths that were called out
- Follow the creative direction provided
- Still push for originality — don't play it safe just because you got notes

For each approach, provide:

1. **Title**: A short, punchy working title for the concept.
2. **Core Idea**: The central creative thought in 1-2 sentences.
3. **Execution**: How this idea comes to life across channels. Be specific.
4. **Why It Works**: Rationale connecting back to the brief and addressing 
   the feedback."""


def run_creative(state: AgencyState) -> AgencyState:
    """Generate three creative approaches based on the creative brief.

    On first iteration, works from the creative brief alone. On subsequent
    iterations, incorporates the Creative Director's feedback.

    Args:
        state: The current agency state containing the creative brief
            and any prior evaluation feedback.

    Returns:
        Updated state with the creative concept and history entry.
    """
    llm = get_llm()
    provider = get_llm_provider()

    # First iteration: work from brief only
    # Subsequent iterations: incorporate CD feedback
    is_revision = state.cd_evaluation is not None

    if is_revision:
        system_prompt = REVISION_PROMPT
        human_content = (
            f"Here is the creative brief:\n\n{state.creative_brief}\n\n"
            f"Here was your previous creative work:\n\n{state.creative_concept}\n\n"
            f"Here is the Creative Director's feedback:\n\n"
            f"Score: {state.cd_evaluation.score}/100\n"
            f"Strengths: {', '.join(state.cd_evaluation.strengths)}\n"
            f"Weaknesses: {', '.join(state.cd_evaluation.weaknesses)}\n"
            f"Direction: {state.cd_evaluation.direction}\n\n"
            "Please produce three improved creative approaches."
        )
    else:
        system_prompt = CREATIVE_SYSTEM_PROMPT
        human_content = (
            f"Here is the creative brief:\n\n{state.creative_brief}\n\n"
            "Please produce three distinct creative approaches."
        )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_content),
    ]

    response = llm.invoke(messages)
    creative_concept = response.content

    # Update state
    state.creative_concept = creative_concept
    state.iteration += 1
    state.status = WorkflowStatus.REVIEW
    state.history.append(
        AgentOutput(
            agent=AgentRole.CREATIVE,
            provider=provider,
            model=get_model_name(provider),
            content=creative_concept,
            timestamp=datetime.utcnow(),
        )
    )

    return state
