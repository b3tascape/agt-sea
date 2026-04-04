"""
agt_sea — Strategist Test Script

Run with: uv run python tests/test_strategist.py

Tests the Strategist agent in isolation with a sample client brief.
This is a manual integration test — it makes a real LLM call.
"""

from agt_sea.agents.strategist import run_strategist
from agt_sea.models.state import AgencyState

from _helpers import load_brief, print_entry_fields


def main():
    brief = load_brief()
    state = AgencyState(client_brief=brief)

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


if __name__ == "__main__":
    main()
