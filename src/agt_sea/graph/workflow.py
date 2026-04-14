"""
agt_sea — Graph Workflow

Defines the LangGraph state graph that orchestrates the full
creative agency pipeline: Strategist → Creative → Creative Director
with conditional approval/revision routing.
"""

from __future__ import annotations

from typing import Callable

from langgraph.graph import StateGraph, END

from agt_sea.models.state import (
    AgencyState,
    AgentRole,
    WorkflowStatus,
)
from agt_sea.agents.strategist import run_strategist
from agt_sea.agents.creative import run_creative
from agt_sea.agents.creative_director import (
    run_creative_director,
    check_approval,
    check_max_iterations,
)


# ---------------------------------------------------------------------------
# Finalisation nodes — handle state changes before the graph ends
# ---------------------------------------------------------------------------

def _finalise_approved(state: AgencyState) -> AgencyState:
    """Mark the workflow as approved."""
    state.status = WorkflowStatus.APPROVED
    return state


def _finalise_failed(state: AgencyState) -> AgencyState:
    """Mark the workflow as failed and ensure an error message is present."""
    if state.error is None:
        state.error = "Unknown failure (no error detail captured)"
    state.status = WorkflowStatus.FAILED
    return state


def _safe_node(
    agent_fn: Callable[[AgencyState], AgencyState],
) -> Callable[[AgencyState], AgencyState]:
    """Wrap an agent node so escaped exceptions become clean FAILED exits.

    Try/except lives at the orchestration layer — agent functions stay clean.
    On exception, the error is written to ``state.error`` and the state is
    returned; routing functions (each guarded with ``if state.error``) then
    divert the run to ``finalise_failed``.

    Bare ``except Exception`` is deliberate: it catches ``pydantic.
    ValidationError`` (including the second-attempt failure re-raised by the
    CD's ``_invoke_with_validation_retry``) via
    ``ValidationError → ValueError → Exception``, but does NOT catch
    ``KeyboardInterrupt`` or ``SystemExit``.
    """
    def wrapped(state: AgencyState) -> AgencyState:
        try:
            return agent_fn(state)
        except Exception as exc:
            # NOTE: state.error format is consumed by
            # frontend/components/error_state.py (Phase 6.1 Step 6). Keep the
            # "<agent_fn> failed: <ExcType>: <msg>" shape stable.
            state.error = (
                f"{agent_fn.__name__} failed: {type(exc).__name__}: {exc}"
            )
            return state

    wrapped.__name__ = f"safe_{agent_fn.__name__}"
    return wrapped


def _check_failed(state: AgencyState) -> str:
    """Pure routing: divert to the failure finaliser when an error is set.

    Shared by the strategist and creative edges — both branches only need
    to know whether the previous node captured an error. The CD's routing
    functions (``check_approval`` / ``check_max_iterations``) carry their
    own error guard at the top of each body to preserve their original
    one-concept names.
    """
    if state.error is not None:
        return "failed"
    return "ok"


def _finalise_max_iterations(state: AgencyState) -> AgencyState:
    """Mark the workflow as max iterations reached and select the
    best-scoring creative concept from history."""
    best_score = -1.0
    best_concept = state.creative_concept  # fallback to latest
    best_iteration = -1
    creative_by_iteration: dict[int, str] = {}

    for entry in state.history:
        if entry.agent == AgentRole.CREATIVE:
            creative_by_iteration[entry.iteration] = entry.content
        if entry.evaluation and entry.evaluation.score > best_score:
            best_score = entry.evaluation.score
            best_iteration = entry.iteration

    if best_iteration in creative_by_iteration:
        best_concept = creative_by_iteration[best_iteration]

    state.creative_concept = best_concept
    state.status = WorkflowStatus.MAX_ITERATIONS_REACHED
    return state


# ---------------------------------------------------------------------------
# Graph definition
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """Build and compile the creative agency workflow graph.

    Graph structure (success path):
        input → strategist → creative → creative_director
            → check_approval
                → approved → finalise_approved → END
                → not_approved → check_iterations
                    → continue → creative (loop)
                    → max_reached → finalise_max_iterations → END

    Failure path (any agent raises):
        _safe_node captures the exception into ``state.error``; the
        following routing function's error guard diverts the run to
        ``finalise_failed`` → END.

    Returns:
        A compiled LangGraph StateGraph ready to invoke.
    """
    graph = StateGraph(AgencyState)

    # --- Add nodes (agents wrapped with _safe_node for orchestration-layer
    # exception handling — agent functions themselves stay untouched) ---
    graph.add_node("strategist", _safe_node(run_strategist))
    graph.add_node("creative", _safe_node(run_creative))
    graph.add_node("creative_director", _safe_node(run_creative_director))
    graph.add_node("check_iterations", lambda state: state)  # pass-through
    graph.add_node("finalise_approved", _finalise_approved)
    graph.add_node("finalise_max_iterations", _finalise_max_iterations)
    graph.add_node("finalise_failed", _finalise_failed)

    # --- Define edges ---
    # Linear flow: strategist → creative → creative_director, each gated
    # by _check_failed so a captured error diverts to finalise_failed.
    graph.set_entry_point("strategist")
    graph.add_conditional_edges(
        "strategist",
        _check_failed,
        {
            "ok": "creative",
            "failed": "finalise_failed",
        },
    )
    graph.add_conditional_edges(
        "creative",
        _check_failed,
        {
            "ok": "creative_director",
            "failed": "finalise_failed",
        },
    )

    # Conditional: creative_director → check approval (with error guard)
    graph.add_conditional_edges(
        "creative_director",
        check_approval,
        {
            "approved": "finalise_approved",
            "not_approved": "check_iterations",
            "failed": "finalise_failed",
        },
    )

    # Second conditional: check iteration limit (with error guard)
    graph.add_conditional_edges(
        "check_iterations",
        check_max_iterations,
        {
            "continue": "creative",
            "max_reached": "finalise_max_iterations",
            "failed": "finalise_failed",
        },
    )

    # Finalisation → END
    graph.add_edge("finalise_approved", END)
    graph.add_edge("finalise_max_iterations", END)
    graph.add_edge("finalise_failed", END)

    return graph.compile()


# Pre-built graph instance for convenience
agency_graph = build_graph()