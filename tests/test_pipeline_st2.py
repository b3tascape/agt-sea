"""
agt_sea — Full Standard 2.0 Pipeline Test

Run with: uv run python tests/test_pipeline_st2.py
Interactive: uv run python -i tests/test_pipeline_st2.py

Manual integration test — makes real LLM calls. Exercises the complete
v2 graph end-to-end:

    strategist_st2 → creative_a_st2 → interrupt → (select territory 0)
        → creative_b_st2 → cd_grader_st2 → [feedback loop] → cd_synthesis_st2 → END

Territory selection is deterministic (index 0) so the test is
reproducible without human interaction. The feedback-loop branch
(rejection → cd_feedback_st2 → creative_b_st2) triggers only if the
grader score falls below ``approval_threshold``; this script accepts
either outcome (APPROVED or MAX_ITERATIONS_REACHED).

Key patterns this test demonstrates for future callers:

* **Thread config is mandatory.** Every ``stream()`` / ``invoke()``
  call on the v2 graph must include
  ``config={"configurable": {"thread_id": "<id>"}}``. The same
  ``thread_id`` links the initial run to the resume call.
* **Detecting the interrupt.** Either watch ``stream()`` for the
  ``__interrupt__`` event, or inspect ``graph.get_state(config).next``
  / ``.interrupts`` after the loop finishes. This test uses the
  snapshot approach because it's simpler for a scripted resume.
* **Resume API.** Pass ``Command(resume=<value>)`` as the input to a
  second ``stream()`` / ``invoke()`` call with the same config. The
  resume value is returned by ``interrupt()`` inside the node.
* **Boundary rehydration is unchanged.** ``graph.get_state(cfg).values``
  is a plain dict — ``AgencyState.model_validate(values)`` still
  applies.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from langgraph.types import Command

from agt_sea.graph.workflow_st2 import agency_graph_st2
from agt_sea.models.state import AgencyState, WorkflowStatus

from _helpers import load_brief, print_entry_fields


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(title)
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)


def main() -> AgencyState:
    brief = load_brief()
    initial_state = AgencyState(client_brief=brief, num_territories=3)

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    print("")
    print("-" * 90)
    print("-" * 90)
    print_header("AGT_SEA — STANDARD 2.0 PIPELINE RUN")
    print(f"\nClient Brief:\n\n{brief}\n")
    print("-" * 60)
    print(f"thread_id: {thread_id}")
    print(f"num_territories: {initial_state.num_territories}")
    print(f"max_iterations: {initial_state.max_iterations}")
    print(f"approval_threshold: {initial_state.approval_threshold}")
    print("-" * 60)

    # --- Phase 1: run until the interrupt pauses the graph ---
    print("\nRunning pipeline until territory-selection interrupt...\n")
    for event in agency_graph_st2.stream(initial_state, config=config):
        # Each event is a dict keyed by node name. Print the key so the
        # progression is visible in the terminal.
        keys = list(event.keys())
        print(f"  event: {keys}")

    paused_snap = agency_graph_st2.get_state(config)
    print_header("PAUSED — TERRITORY SELECTION")
    print(f"Next node: {paused_snap.next}")
    print(f"Interrupts pending: {len(paused_snap.interrupts)}")

    paused_state = AgencyState.model_validate(paused_snap.values)
    assert paused_snap.next == ("interrupt_territory_selection",), (
        f"Expected paused at interrupt node, got {paused_snap.next}"
    )
    assert paused_snap.interrupts, "Expected at least one pending interrupt"
    assert len(paused_state.territories) == initial_state.num_territories, (
        f"Expected {initial_state.num_territories} territories, got "
        f"{len(paused_state.territories)}"
    )

    for idx, territory in enumerate(paused_state.territories, start=1):
        print(f"\n  TERRITORY {idx}: {territory.title}")
        print(f"    Core idea: {territory.core_idea}")
        print(f"    Why it works: {territory.why_it_works}")

    # --- Phase 2: resume with territory[0] ---
    print_header("RESUMING WITH TERRITORY 0")
    selection = {"action": "select", "index": 0}
    print(f"Resume value: {selection}")
    print(f"Selected title: {paused_state.territories[0].title}\n")

    for event in agency_graph_st2.stream(
        Command(resume=selection), config=config
    ):
        keys = list(event.keys())
        print(f"  event: {keys}")

    # --- Phase 3: final state ---
    final_snap = agency_graph_st2.get_state(config)
    final_state = AgencyState.model_validate(final_snap.values)

    print_header("PIPELINE HISTORY")
    for entry in final_state.history:
        print(f"\n--- {entry.agent.value} (iter {entry.iteration}) ---")
        print_entry_fields(entry, indent="  ")
        print("-" * 60)
        # Trim for terminal readability
        snippet = entry.content
        if len(snippet) > 500:
            snippet = snippet[:500] + "..."
        print(snippet)

    print_header("FINAL OUTPUT")
    print(f"Status: {final_state.status}")
    print(f"Total iterations: {final_state.iteration}")
    print(f"History entries: {len(final_state.history)}")

    if final_state.grader_evaluation is not None:
        print(
            f"Final grader score: "
            f"{final_state.grader_evaluation.score}/100"
        )

    # --- Assertions ---
    # The test is reproducible up to the interrupt, but the LLM may
    # score above or below threshold — both APPROVED and
    # MAX_ITERATIONS_REACHED are valid terminal states for a
    # successful run. FAILED indicates an agent raised, which surfaces
    # the error for debugging.
    assert final_state.status in (
        WorkflowStatus.APPROVED,
        WorkflowStatus.MAX_ITERATIONS_REACHED,
    ), (
        f"Expected APPROVED or MAX_ITERATIONS_REACHED, got "
        f"{final_state.status} "
        f"(error: {final_state.error})"
    )
    assert final_state.cd_synthesis is not None, (
        "Expected state.cd_synthesis to be populated by the synthesis node"
    )
    synthesis = final_state.cd_synthesis
    assert synthesis.selected_title.strip(), "Synthesis selected_title is empty"
    assert synthesis.recommendation.strip(), "Synthesis recommendation is empty"
    assert synthesis.comparison_notes is None, (
        "Expected comparison_notes to be None when only one concept was "
        "developed (simplified v2 graph)."
    )

    print("\n" + "-" * 60)
    print(f"SELECTED TITLE: {synthesis.selected_title}")
    print("-" * 60)
    print(f"\nRECOMMENDATION:\n\n{synthesis.recommendation}")
    print("")
    print("=" * 60)
    print("=" * 60)

    return final_state


if __name__ == "__main__":
    final_state = main()
