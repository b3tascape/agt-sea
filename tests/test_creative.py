"""
agt_sea — Strategist → Creative Pipeline Test

Run with: uv run python tests/test_creative.py

Tests the first two agents in sequence with a sample client brief.
This is a manual integration test — it makes real LLM calls.
"""

from pathlib import Path

from agt_sea.agents.strategist import run_strategist
from agt_sea.agents.creative import run_creative
from agt_sea.models.state import AgencyState

# ---------------------------------------------------------------------------
# Load sample brief
# ---------------------------------------------------------------------------

BRIEFS_DIR = Path(__file__).parent.parent / "briefs"


def load_brief(filename: str = "sample_brief_001.txt") -> str:
    """Load a client brief from the briefs directory."""
    brief_path = BRIEFS_DIR / filename
    return brief_path.read_text().strip()


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
    print(f"Agent: {state.history[0].agent}")
    print(f"Provider: {state.history[0].provider}")
    print(f"Model: {state.history[0].model}")
    print(f"Date: {state.history[0].timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
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

    # --- Creative ---
    state = run_creative(state)

    print("\n" + "=" * 60)
    print("=" * 60)
    print("STEP 2: CREATIVE")
    print("=" * 60)
    print("=" * 60)
    print(f"Iteration: {state.iteration}")
    print(f"Status: {state.status}")
    print(f"History entries: {len(state.history)}")
    print(f"Agent: {state.history[1].agent}")
    print(f"Provider: {state.history[1].provider}")
    print(f"Model: {state.history[1].model}")
    print(f"Date: {state.history[1].timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    print("=" * 60)
    print("")
    print(f"Creative Concepts:\n{state.creative_concept}")
    print("")
    print("-" * 60)
    print("-" * 60)
    print("")


if __name__ == "__main__":
    main()