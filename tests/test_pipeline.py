"""
agt_sea — Full Pipeline Test

Run with: uv run python tests/test_pipeline.py
Interactive: uv run python -i tests/test_pipeline.py

Tests the complete agent graph: Strategist → Creative → Creative Director
with the approval/revision loop. This is a manual integration test that
makes real LLM calls.
"""

from datetime import datetime

from agt_sea.graph.workflow import agency_graph
from agt_sea.models.state import AgencyState, AgentRole, WorkflowStatus

from _helpers import load_brief, print_entry_fields


def print_header(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(title)
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 60)


def print_metadata(entry):
    """Print bordered metadata for a history entry."""
    print("=" * 60)
    print_entry_fields(entry, indent="  ")
    print("=" * 60)
    print("")


def main():
    brief = load_brief()
    initial_state = AgencyState(client_brief=brief)

    print("")
    print("-" * 90)
    print("-" * 90)
    print_header("AGT_SEA — FULL PIPELINE RUN")
    print(f"\nClient Brief:\n\n{brief}\n")
    print("-" * 60)
    print(f"Creative Philosophy: {initial_state.creative_philosophy.value}")
    print(f"Approval Threshold: {initial_state.approval_threshold}")
    print(f"Max Iterations: {initial_state.max_iterations}")
    print("-" * 60)

    # --- Run the graph ---
    print("\nRunning pipeline...\n")
    final_state = agency_graph.invoke(initial_state)

    # --- Walk through history ---
    print_header("PIPELINE HISTORY")

    iteration = 0
    for entry in final_state["history"]:
        if entry.agent == AgentRole.STRATEGIST:
            print("\n--- Strategist ------------------------")
            print_metadata(entry)
            print(f"\n  Creative Brief:\n{entry.content[:500]}...")

        elif entry.agent == AgentRole.CREATIVE:
            iteration += 1
            print(f"\n--- Creative (Iteration {iteration}) ------------------------")
            print_metadata(entry)
            print(f"\n  Concepts:\n{entry.content[:500]}...")

        elif entry.agent == AgentRole.CREATIVE_DIRECTOR:
            print(f"\n--- Creative Director (Iteration {iteration}) ------------------------")
            print_metadata(entry)
            print(f"  Strengths: {', '.join(entry.evaluation.strengths)}\n")
            print(f"  Weaknesses: {', '.join(entry.evaluation.weaknesses)}\n")
            print(f"  Direction: {entry.evaluation.direction}")

    # --- Final output ---
    print_header("FINAL OUTPUT")
    print("")
    print("=" * 60)
    print(f"Status: {final_state['status']}")
    print(f"Total Iterations: {final_state['iteration']}")
    print(f"History Entries: {len(final_state['history'])}")
    print("=" * 60)

    if final_state["status"] == WorkflowStatus.APPROVED:
        print("")
        print("-" * 60)
        print("✅ Creative work APPROVED")
        print("-" * 60)
    elif final_state["status"] == WorkflowStatus.MAX_ITERATIONS_REACHED:
        print("")
        print("-" * 60)
        print("\n⚠️  Max iterations reached — outputting best scoring idea")
        print("-" * 60)

    print(f"\nFinal Creative Concept:\n\n{final_state['creative_concept']}")
    print("")
    print("=" * 60)
    print("=" * 60)
    print("")
    print("-" * 90)
    print("-" * 90)
    print("")

    return final_state


if __name__ == "__main__":
    final_state = main()