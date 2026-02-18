"""
agt_sea — Strategist Test Script

Run with: uv run python tests/test_strategist.py

Tests the Strategist agent in isolation with a sample client brief.
This is a manual integration test — it makes a real LLM call.
"""

from pathlib import Path

from agt_sea.agents.strategist import run_strategist
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
    # Load brief
    brief = load_brief()
    
    # Create initial state with the sample brief
    state = AgencyState(client_brief=brief)

    print("")
    print("=" * 60)
    print("STRATEGIST TEST")
    print("=" * 60)
    print(f"\nClient Brief:\n{state.client_brief}")
    print("")
    print("-" * 60)
    print("-" * 60)

    # Run the strategist
    updated_state = run_strategist(state)

    print(f"\nCreative Brief:\n{updated_state.creative_brief}")
    print("")
    print("-" * 60)
    print("-" * 60)
    print("")
    print("=" * 60)
    print("=" * 60)
    print(f"Status: {updated_state.status}")
    print(f"History entries: {len(updated_state.history)}")
    print(f"Agent: {updated_state.history[0].agent}")
    print(f"Provider: {updated_state.history[0].provider}")
    print(f"Model: {updated_state.history[0].model}")
    print("=" * 60)
    print("=" * 60)
    print("")
    


if __name__ == "__main__":
    main()
