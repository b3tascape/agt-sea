"""
agt_sea — Test Script Helpers

Shared utilities for the manual integration test scripts in this
directory. These scripts are run interactively (not via pytest) —
they make real LLM calls and print structured output for inspection.
"""

from __future__ import annotations

from pathlib import Path

from agt_sea.models.state import AgentOutput

BRIEFS_DIR = Path(__file__).parent.parent / "briefs"


def load_brief(filename: str = "sample_brief_001.txt") -> str:
    """Load a client brief from the briefs directory."""
    brief_path = BRIEFS_DIR / filename
    return brief_path.read_text().strip()


def print_entry_fields(entry: AgentOutput, indent: str = "") -> None:
    """Print the standard AgentOutput fields (agent, provider, model,
    iteration, date) plus the CD score when present.

    Args:
        entry: The AgentOutput to print.
        indent: Leading whitespace to prefix each line with.
    """
    print(f"{indent}Agent: {entry.agent}")
    print(f"{indent}Provider: {entry.provider}")
    print(f"{indent}Model: {entry.model}")
    print(f"{indent}Iteration: {entry.iteration}")
    print(f"{indent}Date: {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    if entry.evaluation:
        print(f"{indent}Score: {entry.evaluation.score}/100")
