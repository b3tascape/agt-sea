"""
agt_sea — Pipeline Failure Integration Tests

Forces an exception inside an agent node and asserts the graph reaches
``WorkflowStatus.FAILED`` cleanly — no traceback escapes
``graph.invoke()``.

Run with:
    uv run pytest tests/test_pipeline_failure.py

Patching gotcha — read before editing
--------------------------------------
LangGraph's ``add_node(name, fn)`` captures the function object at
graph-build time. By then, ``agt_sea/graph/workflow.py`` has already done
``from agt_sea.agents.strategist import run_strategist_st1``, which binds
``run_strategist_st1`` as an attribute on the ``agt_sea.graph.workflow``
module — NOT on ``agt_sea.agents.strategist``.

These tests therefore:

1. Monkeypatch ``agt_sea.graph.workflow.<agent_fn>`` (the right reference).
   Patching ``agt_sea.agents.<module>.<fn>`` would silently miss.
2. Call ``build_graph()`` **after** the patch so the compiled graph
   captures the patched symbol. The module-level ``agency_graph`` built
   at import time is NOT used here — it holds the unpatched originals.
"""

from __future__ import annotations

import pytest

from agt_sea.graph import workflow as workflow_module
from agt_sea.models.state import AgencyState, WorkflowStatus


# ---------------------------------------------------------------------------
# Test A — Strategist failure
# ---------------------------------------------------------------------------


def test_strategist_failure_surfaces_as_failed_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A raised exception inside the strategist becomes a FAILED run.

    Exercises: ``_safe_node`` capture → ``_check_failed`` routing →
    ``finalise_failed`` node → END.
    """
    # Stub is named ``run_strategist_st1`` (not ``boom_strategist``) so
    # that ``_safe_node`` reads the production ``__name__`` when
    # formatting ``state.error`` — the test then asserts on the same
    # string users will see in the frontend.
    def run_strategist_st1(state: AgencyState) -> AgencyState:
        raise RuntimeError("strategist boom")

    monkeypatch.setattr(workflow_module, "run_strategist_st1", run_strategist_st1)

    # Rebuild the graph AFTER the patch so the compiled node captures the
    # patched symbol (see module docstring).
    compiled = workflow_module.build_graph()

    initial_state = AgencyState(client_brief="test brief")

    # Assertion: graph.invoke() completes cleanly. No pytest.raises here —
    # that is the point of _safe_node. Any escaped exception fails the test.
    raw = compiled.invoke(initial_state)

    final_state = AgencyState.model_validate(raw)

    assert final_state.status == WorkflowStatus.FAILED
    assert final_state.error is not None
    # Error format is the contract with frontend/components/error_state.py —
    # if this shape changes, that component breaks.
    assert "run_strategist_st1 failed" in final_state.error
    assert "RuntimeError" in final_state.error
    assert "strategist boom" in final_state.error


# ---------------------------------------------------------------------------
# Test B — Creative Director failure (exercises CD routing guards)
# ---------------------------------------------------------------------------


def test_creative_director_failure_surfaces_as_failed_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A raised exception inside the CD becomes a FAILED run.

    Exercises the error guards at the top of ``check_approval`` — without
    them, a crashed CD that never populated ``cd_evaluation`` would hit
    ``AttributeError`` when ``check_approval`` tried to read ``.score``.

    Strategist and creative are stubbed with minimal no-LLM fakes so this
    stays a unit test. The stubs below are intentionally minimal — they
    only populate what downstream routing reads, and ``history`` is left
    empty because this test asserts on ``status`` and ``error`` only.
    """
    # Stubs are named after the real agent functions so ``_safe_node``
    # reads the production ``__name__`` when formatting ``state.error``.
    def run_strategist_st1(state: AgencyState) -> AgencyState:
        # Minimal: only populates creative_brief (read by creative).
        state.creative_brief = "stub brief"
        return state

    def run_creative(state: AgencyState) -> AgencyState:
        # Minimal: only populates creative_concept and bumps iteration.
        state.creative_concept = "stub concept"
        state.iteration += 1
        return state

    def run_creative_director(state: AgencyState) -> AgencyState:
        raise RuntimeError("cd boom")

    monkeypatch.setattr(workflow_module, "run_strategist_st1", run_strategist_st1)
    monkeypatch.setattr(workflow_module, "run_creative", run_creative)
    monkeypatch.setattr(
        workflow_module, "run_creative_director", run_creative_director
    )

    compiled = workflow_module.build_graph()

    initial_state = AgencyState(client_brief="test brief")

    # Assertion: graph.invoke() completes cleanly. No pytest.raises here —
    # that is the point of _safe_node. Any escaped exception fails the test.
    raw = compiled.invoke(initial_state)

    final_state = AgencyState.model_validate(raw)

    assert final_state.status == WorkflowStatus.FAILED
    assert final_state.error is not None
    assert "run_creative_director failed" in final_state.error
    assert "RuntimeError" in final_state.error
    assert "cd boom" in final_state.error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
