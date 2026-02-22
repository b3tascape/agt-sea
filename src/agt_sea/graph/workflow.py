"""
agt_sea — Graph Workflow

Defines the LangGraph state graph that orchestrates the full
creative agency pipeline: Strategist → Creative → Creative Director
with conditional approval/revision routing.
"""

from __future__ import annotations

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


def _finalise_max_iterations(state: AgencyState) -> AgencyState:
    """Mark the workflow as max iterations reached and select the
    best-scoring creative concept from history."""
    best_score = -1.0
    best_concept = state.creative_concept  # fallback to latest

    for entry in state.history:
        if entry.evaluation and entry.evaluation.score > best_score:
            best_score = entry.evaluation.score
            # Find the creative output from the same iteration
            for creative_entry in state.history:
                if (
                    creative_entry.agent == AgentRole.CREATIVE
                    and creative_entry.iteration == entry.iteration
                ):
                    best_concept = creative_entry.content
                    break

    state.creative_concept = best_concept
    state.status = WorkflowStatus.MAX_ITERATIONS_REACHED
    return state


# ---------------------------------------------------------------------------
# Graph definition
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """Build and compile the creative agency workflow graph.

    Graph structure:
        input → strategist → creative → creative_director
            → check_approval
                → approved → finalise_approved → END
                → not_approved → check_iterations
                    → continue → creative (loop)
                    → max_reached → finalise_max_iterations → END

    Returns:
        A compiled LangGraph StateGraph ready to invoke.
    """
    graph = StateGraph(AgencyState)

    # --- Add nodes ---
    graph.add_node("strategist", run_strategist)
    graph.add_node("creative", run_creative)
    graph.add_node("creative_director", run_creative_director)
    graph.add_node("check_iterations", lambda state: state)  # pass-through
    graph.add_node("finalise_approved", _finalise_approved)
    graph.add_node("finalise_max_iterations", _finalise_max_iterations)

    # --- Define edges ---
    # Linear flow: strategist → creative → creative_director
    graph.set_entry_point("strategist")
    graph.add_edge("strategist", "creative")
    graph.add_edge("creative", "creative_director")

    # Conditional: creative_director → check approval
    graph.add_conditional_edges(
        "creative_director",
        check_approval,
        {
            "approved": "finalise_approved",
            "not_approved": "check_iterations",
        },
    )

    # Second conditional: check iteration limit
    graph.add_conditional_edges(
        "check_iterations",
        check_max_iterations,
        {
            "continue": "creative",
            "max_reached": "finalise_max_iterations",
        },
    )

    # Finalisation → END
    graph.add_edge("finalise_approved", END)
    graph.add_edge("finalise_max_iterations", END)

    return graph.compile()


# Pre-built graph instance for convenience
agency_graph = build_graph()