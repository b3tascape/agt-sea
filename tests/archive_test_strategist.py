"""
agt_sea — Strategist Test Script

Run with: uv run python tests/test_strategist.py

Tests the Strategist agent in isolation with a sample client brief.
This is a manual integration test — it makes a real LLM call.
"""

from agt_sea.agents.strategist import run_strategist
from agt_sea.models.state import AgencyState

# ---------------------------------------------------------------------------
# Sample client brief
# ---------------------------------------------------------------------------

SAMPLE_BRIEF = """
We're a mid-sized coffee company called 'Daybreak Coffee' launching a new 
line of cold brew concentrates for the at-home market. 

Our target is millennials and Gen-Z who currently buy iced coffee from cafes 
but are looking to save money without sacrificing quality. 

We need a campaign concept that positions Daybreak as the smarter daily 
ritual — not just cheaper, but a better way to start the day. 

Budget is modest so we're thinking primarily social and digital channels. 
Launch is in 3 months.
"""


def main():
    # Create initial state with the sample brief
    state = AgencyState(client_brief=SAMPLE_BRIEF)

    print("=" * 60)
    print("STRATEGIST TEST")
    print("=" * 60)
    print(f"\nClient Brief:\n{state.client_brief}")
    print("-" * 60)

    # Run the strategist
    updated_state = run_strategist(state)

    print(f"\nCreative Brief:\n{updated_state.creative_brief}")
    print("-" * 60)
    print(f"\nStatus: {updated_state.status}")
    print(f"History entries: {len(updated_state.history)}")
    print(f"Agent: {updated_state.history[0].agent}")
    print(f"Provider: {updated_state.history[0].provider}")
    print("=" * 60)


if __name__ == "__main__":
    main()
