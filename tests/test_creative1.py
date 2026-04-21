"""
agt_sea — Strategist → Creative 1 Pipeline Test (Standard 2.0)

Run with: uv run python tests/test_creative1.py

Tests the Strategist then the Creative 1 territory-generation agent with
a sample client brief and ``num_territories=3``. Manual integration test
— makes real LLM calls.
"""

from agt_sea.agents.creative1 import run_creative1
from agt_sea.agents.strategist import run_strategist
from agt_sea.models.state import AgencyState

from _helpers import load_brief, print_entry_fields


def main() -> None:
    brief = load_brief()
    state = AgencyState(client_brief=brief, num_territories=3)

    # --- Strategist ---
    state = run_strategist(state)

    print("\n" + "=" * 60)
    print("=" * 60)
    print("STEP 1: STRATEGIST")
    print("=" * 60)
    print("=" * 60)
    print(f"Status: {state.status}")
    print(f"History entries: {len(state.history)}")
    print_entry_fields(state.history[0])
    print("-" * 60)
    print("=" * 60)
    print("")
    print(f"Client Brief:\n{state.client_brief}")
    print("")
    print("-" * 60)
    print("-" * 60)
    print("")
    print(f"Creative Brief:\n{state.creative_brief}")
    print("")
    print("-" * 60)
    print("-" * 60)
    print("")

    # --- Creative 1 ---
    state = run_creative1(state)

    print("\n" + "=" * 60)
    print("=" * 60)
    print("STEP 2: CREATIVE 1")
    print("=" * 60)
    print("=" * 60)
    print(f"Status: {state.status}")
    print(f"History entries: {len(state.history)}")
    print_entry_fields(state.history[1])
    print("-" * 60)
    print("=" * 60)
    print("")

    # Assertions — fail fast if the shape is wrong, so the developer
    # doesn't have to eyeball it.
    assert len(state.territories) == 3, (
        f"Expected 3 territories, got {len(state.territories)}"
    )
    for idx, territory in enumerate(state.territories, start=1):
        assert territory.title.strip(), f"Territory {idx} has empty title"
        assert territory.core_idea.strip(), f"Territory {idx} has empty core_idea"
        assert territory.why_it_works.strip(), (
            f"Territory {idx} has empty why_it_works"
        )

    print(f"Territories generated: {len(state.territories)}")
    print("")
    for idx, territory in enumerate(state.territories, start=1):
        print("-" * 60)
        print(f"TERRITORY {idx}: {territory.title}")
        print("-" * 60)
        print(f"Core idea:\n{territory.core_idea}")
        print("")
        print(f"Why it works:\n{territory.why_it_works}")
        print("")


if __name__ == "__main__":
    main()
