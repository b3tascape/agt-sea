"""
agt_sea — Creative Director Agent

Evaluates the Creative agent's output against the creative brief,
returning a structured evaluation with score, strengths, weaknesses,
and direction. Evaluation lens is shaped by the selected creative
philosophy.
"""

from __future__ import annotations

from datetime import UTC, datetime

from langchain_core.messages import SystemMessage, HumanMessage

from agt_sea.llm.provider import get_llm
from agt_sea.models.state import (
    AgencyState,
    AgentOutput,
    AgentRole,
    CDEvaluation,
    CreativePhilosophy,
    WorkflowStatus,
)
from agt_sea.config import get_llm_provider, get_model_name
from agt_sea.prompts.loader import load_philosophy_prompt


def _build_system_prompt(philosophy: CreativePhilosophy) -> str:
    """Build the CD system prompt with the selected creative philosophy."""
    philosophy_text = load_philosophy_prompt(philosophy)

    return f"""You are an experienced Creative Director at a world-class creative agency.

Your creative philosophy:
{philosophy_text}

Your role is to evaluate creative work against the creative brief. You are 
tough but constructive — your job is to push the work to be the best it can 
be, not to tear it down.

When evaluating, consider:
- Does the work answer the brief? Is it on-strategy?
- Is the core idea genuinely original or is it derivative?
- Would this work stand out in the real world?
- Is the execution specific and tangible, or vague and hand-wavy?
- Does it connect to the insight in the brief?

Score the work out of 100:
- 90-100: Exceptional. Ready to present to the client.
- 80-89: Strong. Minor refinements needed but the idea is there.
- 60-79: Promising but needs significant development.
- 40-59: The direction isn't working. Needs a fundamental rethink.
- Below 40: Off-brief or uninspired. Start over.

Be honest. A generous score helps nobody."""


def run_creative_director(state: AgencyState) -> AgencyState:
    """Evaluate the creative concepts and return structured feedback.

    Uses with_structured_output to ensure the LLM returns a valid
    CDEvaluation object with score, strengths, weaknesses, and direction.

    Args:
        state: The current agency state containing the creative brief
            and creative concepts to evaluate.

    Returns:
        Updated state with the CD evaluation and history entry.
    """
    provider = state.llm_provider or get_llm_provider()
    model = state.llm_model or get_model_name(provider)
    llm = get_llm(provider=provider, model=model)

    system_prompt = _build_system_prompt(state.creative_philosophy)

    # Use structured output to get a validated CDEvaluation
    structured_llm = llm.with_structured_output(CDEvaluation)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=(
            f"Here is the creative brief:\n\n{state.creative_brief}\n\n"
            f"Here is the creative work to evaluate (iteration "
            f"{state.iteration}):\n\n{state.creative_concept}\n\n"
            "Please evaluate this work."
        )),
    ]

    evaluation = structured_llm.invoke(messages)

    # Update state
    state.cd_evaluation = evaluation
    state.status = WorkflowStatus.REVIEW
    state.history.append(
        AgentOutput(
            agent=AgentRole.CREATIVE_DIRECTOR,
            provider=provider,
            model=model,
            iteration=state.iteration,
            content=(
                f"Score: {evaluation.score}/100\n"
                f"Strengths: {', '.join(evaluation.strengths)}\n"
                f"Weaknesses: {', '.join(evaluation.weaknesses)}\n"
                f"Direction: {evaluation.direction}"
            ),
            evaluation=evaluation,
            timestamp=datetime.now(UTC),
        )
    )

    return state


# ---------------------------------------------------------------------------
# Routing functions — pure logic, no state mutation
# ---------------------------------------------------------------------------

def check_approval(state: AgencyState) -> str:
    """Routing function: has the creative work met the approval threshold?

    Returns:
        'approved' if score meets threshold, 'not_approved' otherwise.
    """
    if state.cd_evaluation and state.cd_evaluation.score >= state.approval_threshold:
        return "approved"
    return "not_approved"


def check_max_iterations(state: AgencyState) -> str:
    """Routing function: has the iteration limit been reached?

    Returns:
        'max_reached' if at iteration limit, 'continue' otherwise.
    """
    if state.iteration >= state.max_iterations:
        return "max_reached"
    return "continue"