"""
agt_sea — Strategist → Creative A → Creative B (Standard 2.0) Pipeline Test

Run with: uv run python tests/test_creative_b_st2.py

Manual integration test — makes real LLM calls. Exercises the full
initial-path Creative B flow:

    strategist → creative_a (N=3) → pick territory 0 → creative_b

Territory 0 is selected deterministically so the test is reproducible
without human interaction. The revision path (grader + CD Feedback →
re-run) is not covered here — that belongs to the v2 pipeline
integration test (``test_pipeline_st2.py``).

Asserts ``state.campaign_concept`` is populated with non-empty fields
and at least one deliverable. Agent-output history is printed for
eyeballing.
"""

from __future__ import annotations

from agt_sea.agents.creative_a_st2 import run_creative_a_st2
from agt_sea.agents.creative_b_st2 import run_creative_b_st2
from agt_sea.agents.strategist_st2 import run_strategist_st2
from agt_sea.models.state import AgencyState

from _helpers import load_brief, print_entry_fields


def main() -> None:
    brief = load_brief()
    state = AgencyState(client_brief=brief, num_territories=3)

    # --- Strategist ---
    state = run_strategist_st2(state)

    print("\n" + "=" * 60)
    print("=" * 60)
    print("STEP 1: STRATEGIST")
    print("=" * 60)
    print("=" * 60)
    print(f"Status: {state.status}")
    print(f"History entries: {len(state.history)}")
    print_entry_fields(state.history[0])
    print("-" * 60)
    print(f"Creative Brief:\n{state.creative_brief}\n")

    # --- Creative A ---
    state = run_creative_a_st2(state)

    print("\n" + "=" * 60)
    print("=" * 60)
    print("STEP 2: CREATIVE A (territory generation)")
    print("=" * 60)
    print("=" * 60)
    print(f"Status: {state.status}")
    print(f"History entries: {len(state.history)}")
    print_entry_fields(state.history[1])
    print("-" * 60)

    assert len(state.territories) == 3, (
        f"Expected 3 territories, got {len(state.territories)}"
    )
    for idx, territory in enumerate(state.territories, start=1):
        print(f"\nTERRITORY {idx}: {territory.title}")
        print(f"  Core idea: {territory.core_idea}")
        print(f"  Why it works: {territory.why_it_works}")

    # --- Territory selection ---
    # Pick territory 0 deterministically — no human in this test.
    state.selected_territory = state.territories[0]
    print("\n" + "-" * 60)
    print(f"Selected territory: {state.selected_territory.title}")
    print("-" * 60)

    # --- Creative B ---
    state = run_creative_b_st2(state)

    print("\n" + "=" * 60)
    print("=" * 60)
    print("STEP 3: CREATIVE B (campaign development)")
    print("=" * 60)
    print("=" * 60)
    print(f"Status: {state.status}")
    print(f"History entries: {len(state.history)}")
    print_entry_fields(state.history[2])
    print("-" * 60)

    # Assertions — fail fast if the shape is wrong so the developer
    # doesn't have to eyeball it.
    assert state.campaign_concept is not None, (
        "Expected state.campaign_concept to be populated"
    )
    concept = state.campaign_concept
    assert concept.title.strip(), "Campaign concept title is empty"
    assert concept.core_idea.strip(), "Campaign concept core_idea is empty"
    assert concept.why_it_works.strip(), "Campaign concept why_it_works is empty"
    assert len(concept.deliverables) >= 1, (
        "Expected at least one deliverable on the campaign concept"
    )
    for i, deliverable in enumerate(concept.deliverables, start=1):
        assert deliverable.name.strip(), f"Deliverable {i} has empty name"
        assert deliverable.explanation.strip(), (
            f"Deliverable {i} has empty explanation"
        )

    print(f"\nCAMPAIGN: {concept.title}")
    print(f"\nCore idea:\n{concept.core_idea}")
    print(f"\nWhy it works:\n{concept.why_it_works}")
    print(f"\nDeliverables ({len(concept.deliverables)}):")
    for i, deliverable in enumerate(concept.deliverables, start=1):
        print(f"\n  {i}. {deliverable.name}")
        print(f"     {deliverable.explanation}")


if __name__ == "__main__":
    main()
