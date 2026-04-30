"""
agt_sea — Territory Cards Component

Renders a list of creative territories (Creative A output) as
independent modular blocks. Each territory is a bordered container with
title, core idea, and why-it-works — the three fields of the Territory
model — laid out so they read as parallel options, not a ranked list.

Pure display: accepts a `list[Territory]` and nothing else. The component
must not read from or write to `st.session_state`, so future callers
(e.g. the Workflow page's territory-selection interrupt UI in Phase E)
can layer selection behaviour on top without the component needing to
know about it.
"""

from __future__ import annotations

import streamlit as st

from agt_sea.models.state import Territory


def render_territory_cards(territories: list[Territory]) -> None:
    """Render territories as independent bordered cards.

    Layout rules (N = `num_territories`, bounded 1–12 on state):
        - N ≤ 3 → single row of N columns, equal width.
        - N ≥ 4 → rows of 3 with whatever remainder falls out
          (5 = 3+2, 7 = 3+3+1, 12 = 3+3+3+3). Orphan rows are accepted
          — users at larger counts have opted into density over symmetry,
          and a bespoke N=4 special case would only look inconsistent
          against 5, 6, 7+.

    Args:
        territories: The Creative A territory list.
    """
    if not territories:
        return

    n = len(territories)
    columns_per_row = n if n <= 3 else 3

    for row_start in range(0, n, columns_per_row):
        row = territories[row_start : row_start + columns_per_row]
        columns = st.columns(columns_per_row)
        for column, territory in zip(columns, row):
            with column:
                _render_card(territory)


def _render_card(territory: Territory) -> None:
    """Render a single territory inside a bordered container.

    Title uses markdown h4 — styled by the theme's ``.stApp h4`` rule
    (Cormorant Garamond). The body lives in ``render_territory_body()``
    so the same field rendering can be reused (e.g. by the selected-
    territory expander on the Workflow v2 tab).
    """
    with st.container(border=True):
        render_territory_body(territory)


def render_territory_body(territory: Territory) -> None:
    """Render a Territory's three fields without any card boundary.

    Lifted out of ``_render_card`` so callers that have their own
    container (e.g. an expander) can render the same content without
    nesting bordered containers. Field labels use a raw-HTML
    ``territory-label`` class to opt out of the global
    ``.stColumn .stMarkdown strong`` rule, which otherwise forces
    Montserrat caps on bold text inside columns.

    Args:
        territory: The Territory whose fields to render.
    """
    st.markdown(f"#### {territory.title}")
    st.markdown(
        "<p class='territory-label'>CORE IDEA</p>",
        unsafe_allow_html=True,
    )
    st.markdown(territory.core_idea)
    st.markdown(
        "<p class='territory-label'>WHY IT WORKS</p>",
        unsafe_allow_html=True,
    )
    st.markdown(territory.why_it_works)
