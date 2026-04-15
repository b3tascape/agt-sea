"""
agt_sea — Run Guard Component

Per-session run counter for demo abuse mitigation. Caps how many
agent-invoking runs a user can trigger before refreshing the session.
See ADR 0013 for the rationale — this is a speed bump, not a wall.

The gate is a single function: check_run_allowed() both reads and
increments the counter in one call, so callers can't forget to bump
it after a successful check.
"""

from __future__ import annotations

from typing import MutableMapping

import streamlit as st

from agt_sea.config import DEMO_RUN_CAP


def _check_and_increment(
    state: MutableMapping[str, int],
    cap: int,
    key: str = "run_count",
) -> bool:
    """Check the counter against the cap; increment on success.

    Pure helper that operates on any mutable mapping, so the logic
    is testable without a Streamlit session. Returns True if the run
    is allowed (and increments the counter), False if the cap has
    been reached (counter left unchanged).
    """
    current = state.get(key, 0)
    if current >= cap:
        return False
    state[key] = current + 1
    return True


def check_run_allowed() -> bool:
    """Check whether the current session may start another agent run.

    Reads st.session_state.run_count, compares against DEMO_RUN_CAP,
    and increments the counter when the run is allowed. Returns False
    when the cap has been reached so the caller can render the limit
    message and halt the script.
    """
    return _check_and_increment(st.session_state, DEMO_RUN_CAP)


def render_run_limit_reached() -> None:
    """Render the 'demo limit reached' UI."""
    st.warning(
        f"**<<< ! Demo limit reached ! >>>**  \n"
        f"You've used all {DEMO_RUN_CAP} runs available in this session. "
        f"Please refresh the page to start a new session."
    )
