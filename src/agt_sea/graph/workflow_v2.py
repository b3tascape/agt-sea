"""
agt_sea — Graph Workflow (Standard 2.0)

Multi-stage pipeline (ADR 0014): Strategist -> Creative 1 (territories)
-> human interrupt (territory selection) -> Creative 2 (campaign
concept) -> CD Grader -> [CD Feedback loop | CD Synthesis] -> END.

Differences from ``workflow.py`` (Standard 1.0) that matter to readers:

1. **Checkpointer is required** — LangGraph's ``interrupt()`` primitive
   only works when the compiled graph is given a checkpointer. We use
   ``MemorySaver`` for zero-dependency, in-memory persistence. The
   checkpointer is instantiated at **module scope** (see ``_CHECKPOINTER``
   below) and shared across every ``build_graph_v2()`` call — this is
   deliberate: Streamlit re-runs the whole page script on every user
   interaction, which means ``build_graph_v2()`` is called afresh each
   time. A per-call ``MemorySaver()`` would erase in-flight interrupts
   on the next rerun. A module-level singleton survives within the
   Python process. It does NOT survive a process restart / redeploy —
   persistent checkpointing (SQLite / Postgres) is the upgrade path
   when that matters.

2. **Interrupt node must be side-effect-free.** LangGraph resumes an
   interrupted node by **re-executing it from the top** — everything
   above the ``interrupt()`` call runs a second time on every resume.
   Consequence: the interrupt node must not append to history, bump
   counters, or perform anything non-idempotent. ``_interrupt_territory_selection``
   only reads ``state.territories`` and sets a small set of fields. Do
   not add side effects here.

3. **Safe-node wrapper lets GraphBubbleUp propagate.** ``GraphInterrupt``
   (the exception ``interrupt()`` raises) is an ``Exception`` subclass,
   which means v1's naive ``except Exception`` in ``_safe_node`` would
   swallow it and turn the pause into a FAILED run. The v2 wrapper
   ``_safe_node`` catches only "real" exceptions and re-raises anything
   derived from ``GraphBubbleUp`` (the LangGraph control-flow base
   class) so the runtime can handle it. v1's wrapper is unchanged —
   v1 has no interrupts.

4. **Boundary rehydration is identical to v1.** The graph returns a
   plain dict on ``invoke()`` / ``stream()``. Call sites must rehydrate
   with ``AgencyState.model_validate(raw)`` before using attribute
   access. For interrupted runs, the paused state is read via
   ``graph.get_state(config).values`` (also a dict — rehydrate it the
   same way). See ``tests/test_pipeline_v2.py`` for the canonical
   pattern.

5. **Thread config is mandatory.** Every ``graph.invoke()`` /
   ``graph.stream()`` call on the v2 graph must include
   ``config={"configurable": {"thread_id": "<id>"}}`` — LangGraph
   raises ``ValueError`` otherwise. Callers choose the thread_id; the
   same value must be reused on resume to hit the right checkpoint.
"""

from __future__ import annotations

from typing import Callable

from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import GraphBubbleUp
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from agt_sea.agents.cd_feedback_st2 import run_cd_feedback_st2
from agt_sea.agents.cd_grader_st2 import run_cd_grader_st2
from agt_sea.agents.cd_synthesis_st2 import run_cd_synthesis_st2
from agt_sea.agents.creative_a_st2 import run_creative_a_st2
from agt_sea.agents.creative_b_st2 import run_creative_b_st2
from agt_sea.agents.strategist_st2 import run_strategist_st2
from agt_sea.graph.workflow import format_node_error
from agt_sea.models.state import AgencyState, WorkflowStatus


# ---------------------------------------------------------------------------
# Module-level checkpointer singleton
# ---------------------------------------------------------------------------
#
# Instantiated once at import time. Every call to ``build_graph_v2()``
# passes this same instance to ``StateGraph.compile(checkpointer=...)``,
# so interrupted runs survive Streamlit's per-interaction script reruns
# within a process. See the module docstring for the rationale.

_CHECKPOINTER = MemorySaver()


# ---------------------------------------------------------------------------
# Safe-node wrapper — v2 variant that lets GraphBubbleUp propagate
# ---------------------------------------------------------------------------


def _safe_node(
    agent_fn: Callable[[AgencyState], AgencyState],
) -> Callable[[AgencyState], AgencyState]:
    """Wrap an agent node so escaped exceptions become clean FAILED exits.

    Differs from v1's ``_safe_node`` in one important respect: it
    re-raises ``GraphBubbleUp``. ``GraphInterrupt`` (and any other
    LangGraph control-flow signal) inherits from ``GraphBubbleUp`` but
    is ultimately an ``Exception`` subclass, so a bare ``except Exception``
    would swallow it. That would break the interrupt — the runtime needs
    to see the signal to pause.

    On a real exception, the canonical error string is written to
    ``state.error`` (using the shared ``format_node_error`` helper from
    v1) and the state is returned; routing functions, each guarded with
    ``if state.error is not None: return "failed"``, then divert the run
    to ``finalise_failed``.
    """
    def wrapped(state: AgencyState) -> AgencyState:
        try:
            return agent_fn(state)
        except GraphBubbleUp:
            # Control-flow signals (GraphInterrupt and friends) must
            # reach the runtime — never swallow them.
            raise
        except Exception as exc:
            state.error = format_node_error(agent_fn.__name__, exc)
            return state

    wrapped.__name__ = f"safe_{agent_fn.__name__}"
    return wrapped


# ---------------------------------------------------------------------------
# Interrupt node — human-in-the-loop territory selection
# ---------------------------------------------------------------------------


def _interrupt_territory_selection(state: AgencyState) -> AgencyState:
    """Pause the graph until the user picks a territory or asks for a rerun.

    Idempotency contract: this node re-executes in full on every resume
    (LangGraph's documented behaviour). Do not append to ``state.history``,
    do not bump counters, do not call out to LLMs. The only mutations
    safe to perform are the ones derived from the resume value, after
    ``interrupt()`` returns — mutations made *before* the ``interrupt()``
    call are not captured in the paused checkpoint (LangGraph snapshots
    at the boundary of the previous node, not at the start of the
    interrupted one), so they would be lost on resume anyway.

    The paused-state signal is therefore LangGraph's own:
    ``graph.get_state(config).interrupts`` (or ``snap.next ==
    ("interrupt_territory_selection",)``, or the ``__interrupt__`` event
    in ``stream()``). No ``WorkflowStatus`` mirror exists — it wouldn't
    persist through the checkpoint, so keeping one would lie.

    Resume-value contract (dict):

    * ``{"action": "select", "index": int}`` — pick the territory at
      that index in ``state.territories``.
    * ``{"action": "rerun", "rejection_context": str | None}`` — loop
      back to Creative 1 with optional steering text.

    The payload surfaced to the client at ``interrupt()`` is a plain
    dict with the generated territories so Streamlit / a test harness
    can render them without importing the Pydantic models.
    """
    resume_value: dict = interrupt(
        {
            "reason": "territory_selection",
            "territories": [t.model_dump() for t in state.territories],
            "iteration": state.iteration,
        }
    )

    action = resume_value.get("action")
    if action == "rerun":
        # Clear any prior selection and carry optional steering forward.
        state.selected_territory = None
        state.territory_rejection_context = resume_value.get(
            "rejection_context"
        )
    elif action == "select":
        index = resume_value["index"]
        state.selected_territory = state.territories[index]
        # Clear rerun steering now that we're moving to campaign
        # development — stale context would otherwise leak into a later
        # rerun in the same run.
        state.territory_rejection_context = None
    else:
        raise ValueError(
            f"interrupt_territory_selection: unknown resume action "
            f"{action!r}. Expected 'select' or 'rerun'."
        )

    return state


# ---------------------------------------------------------------------------
# Finalisation nodes
# ---------------------------------------------------------------------------


def _finalise_approved(state: AgencyState) -> AgencyState:
    """Mark the workflow as approved."""
    state.status = WorkflowStatus.APPROVED
    return state


def _finalise_max_iterations(state: AgencyState) -> AgencyState:
    """Mark the workflow as max-iterations-reached.

    Unlike v1, v2 does NOT perform best-of restoration of a prior
    campaign concept. Only one ``CampaignConcept`` lives on state at a
    time (each Creative 2 revision overwrites the previous), and the
    history stores rendered-text copies rather than typed snapshots.
    The latest campaign — the one the final grader saw — is what
    ``state.campaign_concept`` already holds, so we leave it in place.
    CD Synthesis then evaluates that campaign for the user-facing
    narrative.

    If per-iteration best-of becomes a requirement we'd add a
    ``campaign_concept_history: list[CampaignConcept]`` on state; that
    is out of scope for Phase D (ADR 0014).
    """
    state.status = WorkflowStatus.MAX_ITERATIONS_REACHED
    return state


def _finalise_failed(state: AgencyState) -> AgencyState:
    """Mark the workflow as failed and ensure an error message is present."""
    if state.error is None:
        state.error = "Unknown failure (no error detail captured)"
    state.status = WorkflowStatus.FAILED
    return state


# ---------------------------------------------------------------------------
# Routing functions — pure, return strings only
# ---------------------------------------------------------------------------


def _check_failed(state: AgencyState) -> str:
    """Shared failure-guard router used on every linear edge.

    Same shape as v1's ``_check_failed``: ``ok`` when no error,
    ``failed`` when a node captured one into ``state.error``.
    """
    if state.error is not None:
        return "failed"
    return "ok"


def _route_after_interrupt(state: AgencyState) -> str:
    """Route the post-interrupt edge.

    ``failed`` short-circuits to the failure finaliser if a prior node
    or the interrupt node itself captured an error. ``selected`` routes
    to Creative 2 when the user picked a territory. ``rerun`` loops
    back to Creative 1 with the optional rejection context already on
    state.
    """
    if state.error is not None:
        return "failed"
    if state.selected_territory is not None:
        return "selected"
    return "rerun"


def _check_approval(state: AgencyState) -> str:
    """Route after the CD Grader.

    * ``failed`` — a prior node captured an error.
    * ``approved`` — score meets threshold. Go to synthesis.
    * ``rejected_budget`` — below threshold, iterations remain. Loop
      via CD Feedback.
    * ``rejected_exhausted`` — below threshold, iteration cap hit.
      Skip feedback, go straight to synthesis for a best-of narrative.
    """
    if state.error is not None:
        return "failed"
    evaluation = state.grader_evaluation
    if evaluation is not None and evaluation.score >= state.approval_threshold:
        return "approved"
    if state.iteration >= state.max_iterations:
        return "rejected_exhausted"
    return "rejected_budget"


def _route_after_synthesis(state: AgencyState) -> str:
    """Route after CD Synthesis decides approved vs max-reached.

    Synthesis runs on both the approved and exhausted paths. We use the
    final grader score to pick the correct finaliser. This re-reads the
    same fields ``_check_approval`` already looked at — the alternative
    (marking the path with a state flag before synthesis) adds a field
    without meaningfully improving clarity.
    """
    if state.error is not None:
        return "failed"
    evaluation = state.grader_evaluation
    if evaluation is not None and evaluation.score >= state.approval_threshold:
        return "approved"
    return "max_reached"


# ---------------------------------------------------------------------------
# Graph definition
# ---------------------------------------------------------------------------


def build_graph_v2() -> StateGraph:
    """Build and compile the Standard 2.0 creative agency workflow graph.

    Graph structure (success path):
        START -> strategist_st2 -> creative_a_st2 -> interrupt_territory_selection
            -> (rerun) -> creative_a_st2 (loop)
            -> (select) -> creative_b_st2 -> cd_grader_st2
                -> approved -> cd_synthesis_st2 -> finalise_approved -> END
                -> rejected + budget -> cd_feedback_st2 -> creative_b_st2 (loop)
                -> rejected + exhausted -> cd_synthesis_st2 -> finalise_max_iterations -> END

    Failure path (any agent raises a non-control-flow exception):
        _safe_node writes the error string into ``state.error``; the
        next routing function's error guard diverts to ``finalise_failed``.

    Returns:
        A compiled LangGraph StateGraph, with the module-scope
        ``_CHECKPOINTER`` attached. Callers must pass
        ``config={"configurable": {"thread_id": "<id>"}}`` on every
        ``invoke()`` / ``stream()``.
    """
    graph = StateGraph(AgencyState)

    # --- Agent nodes (every one wrapped; wrapper re-raises GraphBubbleUp) ---
    graph.add_node("strategist_st2", _safe_node(run_strategist_st2))
    graph.add_node("creative_a_st2", _safe_node(run_creative_a_st2))
    graph.add_node(
        "interrupt_territory_selection",
        _safe_node(_interrupt_territory_selection),
    )
    graph.add_node("creative_b_st2", _safe_node(run_creative_b_st2))
    graph.add_node("cd_grader_st2", _safe_node(run_cd_grader_st2))
    graph.add_node("cd_feedback_st2", _safe_node(run_cd_feedback_st2))
    graph.add_node("cd_synthesis_st2", _safe_node(run_cd_synthesis_st2))

    # --- Finalisation nodes (unwrapped — they own state.status mutation) ---
    graph.add_node("finalise_approved", _finalise_approved)
    graph.add_node("finalise_max_iterations", _finalise_max_iterations)
    graph.add_node("finalise_failed", _finalise_failed)

    # --- Edges ---
    graph.set_entry_point("strategist_st2")

    graph.add_conditional_edges(
        "strategist_st2",
        _check_failed,
        {"ok": "creative_a_st2", "failed": "finalise_failed"},
    )
    graph.add_conditional_edges(
        "creative_a_st2",
        _check_failed,
        {"ok": "interrupt_territory_selection", "failed": "finalise_failed"},
    )
    graph.add_conditional_edges(
        "interrupt_territory_selection",
        _route_after_interrupt,
        {
            "selected": "creative_b_st2",
            "rerun": "creative_a_st2",
            "failed": "finalise_failed",
        },
    )
    graph.add_conditional_edges(
        "creative_b_st2",
        _check_failed,
        {"ok": "cd_grader_st2", "failed": "finalise_failed"},
    )
    graph.add_conditional_edges(
        "cd_grader_st2",
        _check_approval,
        {
            "approved": "cd_synthesis_st2",
            "rejected_budget": "cd_feedback_st2",
            "rejected_exhausted": "cd_synthesis_st2",
            "failed": "finalise_failed",
        },
    )
    graph.add_conditional_edges(
        "cd_feedback_st2",
        _check_failed,
        {"ok": "creative_b_st2", "failed": "finalise_failed"},
    )
    graph.add_conditional_edges(
        "cd_synthesis_st2",
        _route_after_synthesis,
        {
            "approved": "finalise_approved",
            "max_reached": "finalise_max_iterations",
            "failed": "finalise_failed",
        },
    )

    graph.add_edge("finalise_approved", END)
    graph.add_edge("finalise_max_iterations", END)
    graph.add_edge("finalise_failed", END)

    return graph.compile(checkpointer=_CHECKPOINTER)


# Pre-built graph instance for convenience. Shares ``_CHECKPOINTER``
# with every other ``build_graph_v2()`` call in the process.
agency_graph_v2 = build_graph_v2()
