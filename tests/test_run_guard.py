"""
agt_sea — Run Guard Unit Tests

Unit tests for the per-session run counter used by the demo abuse
mitigation (ADR 0013).

Run with:
    uv run pytest tests/test_run_guard.py

The pure helper `_check_and_increment` operates on any mutable mapping,
so the tests pass a plain dict and never touch Streamlit's session state.
The public `check_run_allowed()` wrapper is a thin adapter around it.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `frontend` importable the same way app.py does at runtime.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "frontend"))

from components.run_guard import _check_and_increment  # noqa: E402


def test_fresh_state_allowed_and_increments() -> None:
    state: dict[str, int] = {}
    assert _check_and_increment(state, cap=10) is True
    assert state["run_count"] == 1


def test_at_cap_minus_one_allowed_and_increments_to_cap() -> None:
    state = {"run_count": 9}
    assert _check_and_increment(state, cap=10) is True
    assert state["run_count"] == 10


def test_at_cap_blocked_and_unchanged() -> None:
    state = {"run_count": 10}
    assert _check_and_increment(state, cap=10) is False
    assert state["run_count"] == 10


def test_over_cap_blocked_and_unchanged() -> None:
    state = {"run_count": 15}
    assert _check_and_increment(state, cap=10) is False
    assert state["run_count"] == 15


def test_cap_of_zero_blocks_immediately() -> None:
    state: dict[str, int] = {}
    assert _check_and_increment(state, cap=0) is False
    assert state.get("run_count", 0) == 0


def test_cap_override_blocks_below_default() -> None:
    state = {"run_count": 9}
    assert _check_and_increment(state, cap=5) is False
    assert state["run_count"] == 9
