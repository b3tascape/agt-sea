"""
agt_sea — Creative Director Agent

Evaluates the Creative agent's output against the creative brief,
returning a structured evaluation with score, strengths, weaknesses,
and direction. Evaluation lens is shaped by the selected creative
philosophy.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from pydantic import ValidationError

from agt_sea.llm.provider import get_llm, wrap_with_transport_retry
from agt_sea.models.state import (
    AgencyState,
    AgentOutput,
    AgentRole,
    CDEvaluation,
    CreativePhilosophy,
    WorkflowStatus,
)
from agt_sea.config import get_llm_provider, get_model_name
from agt_sea.prompts.loader import load_creative_philosophy

logger = logging.getLogger(__name__)


def _build_system_prompt(philosophy: CreativePhilosophy) -> str:
    """Build the CD system prompt with the selected creative philosophy.

    When philosophy is NEUTRAL, no philosophy section is injected — the
    prompt reads as if the feature wasn't there at all.
    """
    philosophy_section = ""
    if philosophy != CreativePhilosophy.NEUTRAL:
        philosophy_text = load_creative_philosophy(philosophy)
        philosophy_section = f"\nYour creative philosophy:\n{philosophy_text}\n"

    return f"""You are an experienced Creative Director at a world-class creative agency.
{philosophy_section}
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


def _invoke_with_validation_retry(
    structured_llm: Runnable[Any, CDEvaluation],
    messages: list[BaseMessage],
) -> CDEvaluation:
    """Invoke a structured-output runnable and reprompt once on ValidationError.

    Schema validation errors only surface *after* a successful network call,
    when the structured-output parser rebuilds a CDEvaluation from the model
    response. That makes them an application-layer concern, not a transport
    one — transport retries (wrapped inside ``structured_llm`` at composition
    time) fire during the network call and can't recover a malformed-but-
    delivered response.

    This helper adds a one-shot reprompt: on the first ``ValidationError`` it
    appends a ``HumanMessage`` describing the failure and calls ``.invoke()``
    once more. A second failure propagates to the caller so the orchestration-
    layer safe-node wrapper can surface it as a FAILED run.

    Args:
        structured_llm: The already-composed structured-output runnable
            (transport retry wrapped around ``.with_structured_output()``).
        messages: The prompt messages to send on the first attempt.

    Returns:
        A validated CDEvaluation from whichever attempt succeeds.

    Raises:
        pydantic.ValidationError: If both attempts fail schema validation.
    """
    try:
        return structured_llm.invoke(messages)
    except ValidationError as exc:
        logger.warning(
            "CD structured output failed validation on first attempt, "
            "retrying with reprompt: %s",
            exc,
        )
        reprompt = messages + [
            HumanMessage(
                content=(
                    "Your previous response failed schema validation:\n\n"
                    f"{exc}\n\n"
                    "Return a new response that conforms exactly to the "
                    "CDEvaluation schema. Do not apologise or explain — "
                    "return only the corrected structured output."
                )
            )
        ]
        return structured_llm.invoke(reprompt)


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
    # Transport retries can't wrap a BaseChatModel before .with_structured_output()
    # is applied — .with_retry() returns a RunnableRetry that has no
    # with_structured_output method. So we fetch the raw chat model, apply
    # structured output, then wrap the composed runnable with transport retry.
    llm = get_llm(provider=provider, model=model, with_retry=False)

    system_prompt = _build_system_prompt(state.cd_philosophy)

    # Use structured output to get a validated CDEvaluation, then wrap the
    # composed runnable with transport-level retries.
    structured_llm = wrap_with_transport_retry(
        llm.with_structured_output(CDEvaluation), provider
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=(
            f"Here is the creative brief:\n\n{state.creative_brief}\n\n"
            f"Here is the creative work to evaluate (iteration "
            f"{state.iteration}):\n\n{state.creative_concept}\n\n"
            "Please evaluate this work."
        )),
    ]

    evaluation = _invoke_with_validation_retry(structured_llm, messages)

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