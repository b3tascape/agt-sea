"""
agt_sea — Workflow Page

Full creative campaign pipeline. Two tabs:

* **Standard 2.0** (default, left) — multi-stage pipeline with
  territory-selection interrupt (ADR 0014). Strategist → Creative A
  (territories) → human selection → Creative B (campaign) → CD Grader
  → [CD Feedback loop | CD Synthesis] → END.
* **Standard 1.0** (right) — original pipeline, unchanged: Strategist
  → Creative → CD loop.

The Standard 2.0 tab drives the interrupt/resume flow via four
session-state keys (all prefixed ``v2_``):

* ``v2_brief_input`` (``str``) — persisted brief so the textarea
  survives page switches.
* ``v2_thread_id`` (``str | None``) — UUID generated per run; the same
  ID links the initial invoke and every resume through the v2 graph's
  module-scope MemorySaver.
* ``v2_phase`` (``"idle" | "interrupted" | "terminal"``) — explicit
  three-state machine driving UI dispatch between reruns. "idle" is
  pre-run or post-reset; "interrupted" is paused at the territory
  selection interrupt; "terminal" is END-reached (APPROVED,
  MAX_ITERATIONS_REACHED, or FAILED).
* ``v2_pending_action`` (``dict | None``) — deferred-stream queue. A
  button click sets this to ``{"kind": "initial"}`` /
  ``{"kind": "select", "index": int}`` / ``{"kind": "rerun",
  "context": str | None}`` and calls ``st.rerun()``; the next script
  run pops it atomically at the top of the handler and invokes the
  corresponding stream. Popping (not get-then-clear) is deliberate:
  widget re-renders during streaming could otherwise double-consume.

Two distinct concerns coexist during streaming and must stay separate:

1. **Live progress display** uses the per-node events that
   ``stream()`` yields. Purely a UI concern — fed to
   ``render_node_progress()`` and gone at the next rerun.
2. **Authoritative state** is read via ``agency_graph_st2.get_state(cfg)
   .values`` after the stream loop ends, then rehydrated with
   ``AgencyState.model_validate(...)``. This is what drives the
   ``v2_phase`` transition, the territory-selection UI, and the
   terminal render. The event stream is not the source of truth on
   v2 — the checkpointer is.
"""

from __future__ import annotations

import uuid

import streamlit as st
from langgraph.types import Command

from agt_sea.graph.workflow_st1 import build_graph_st1
from agt_sea.graph.workflow_st2 import agency_graph_st2
from agt_sea.models.state import AgencyState, Territory, WorkflowStatus

from components.error_state import render_error_state
from components.footer import render_footer
from components.history import render_history
from components.progress import render_node_progress
from components.run_guard import check_run_allowed, render_run_limit_reached
from components.run_metadata import render_run_metadata
from components.synthesis_output import render_synthesis_output
from components.territory_cards import render_territory_body, render_territory_cards


# ---------------------------------------------------------------------------
# Page shell
# ---------------------------------------------------------------------------

st.title("_workflow")

tab_v2, tab_v1 = st.tabs(["standard_st2", "standard_st1"])


# ===========================================================================
# Standard 2.0 — multi-stage pipeline with territory-selection interrupt
# ===========================================================================

def _reset_v2_session() -> None:
    """Clear v2 session-state keys so a new run starts from idle.

    Called before each new initial run so stale checkpointer state
    (belonging to a prior thread_id) doesn't influence the new run's
    UI dispatch.
    """
    st.session_state.v2_thread_id = None
    st.session_state.v2_phase = "idle"
    st.session_state.pop("v2_pending_action", None)
    st.session_state.pop("v2_selected_territory_preview", None)


def _v2_thread_config() -> dict:
    """Build the LangGraph thread config for the active v2 run.

    Every invoke() / stream() / get_state() on the v2 graph must carry
    ``config={"configurable": {"thread_id": <id>}}`` — see ADR 0014 and
    the workflow_st2 module docstring.
    """
    return {"configurable": {"thread_id": st.session_state.v2_thread_id}}


def _v2_update_phase_from_graph() -> None:
    """Read the checkpointer snapshot and set ``v2_phase`` accordingly.

    Called after every stream call. The authoritative phase is derived
    from ``snapshot.next``:

    * ``("interrupt_territory_selection",)`` → paused at the interrupt.
    * ``()`` → the graph reached END (terminal state — success, failure,
      or max-iterations).
    * anything else → treat as terminal and let the terminal UI render
      whatever ``state.status`` reports (usually FAILED).
    """
    snap = agency_graph_st2.get_state(_v2_thread_config())
    if snap.next == ("interrupt_territory_selection",):
        st.session_state.v2_phase = "interrupted"
    else:
        st.session_state.v2_phase = "terminal"


def _v2_run_initial_stream(brief_text: str) -> None:
    """Construct the initial AgencyState and stream to the first pause.

    Renders a progress container with per-node status widgets as the
    stream yields. The checkpointer holds the authoritative state; we
    consult it via ``_v2_update_phase_from_graph()`` once streaming ends.
    """
    initial_state = AgencyState(
        client_brief=brief_text,
        strategist_st2_strategic_philosophy=st.session_state.strategist_st2_strategic_philosophy,
        creative_a_st2_creative_philosophy=st.session_state.creative_a_st2_creative_philosophy,
        creative_b_st2_creative_philosophy=st.session_state.creative_b_st2_creative_philosophy,
        creative_director_st2_creative_philosophy=st.session_state.creative_director_st2_creative_philosophy,
        creative_a_st2_provenance=st.session_state.creative_a_st2_provenance,
        creative_a_st2_taste=st.session_state.creative_a_st2_taste,
        creative_b_st2_provenance=st.session_state.creative_b_st2_provenance,
        creative_b_st2_taste=st.session_state.creative_b_st2_taste,
        creative_director_st2_provenance=st.session_state.creative_director_st2_provenance,
        creative_director_st2_taste=st.session_state.creative_director_st2_taste,
        creative_a_st2_temperature=st.session_state.creative_a_st2_temperature,
        creative_b_st2_temperature=st.session_state.creative_b_st2_temperature,
        cd_grader_st2_temperature=st.session_state.cd_grader_st2_temperature,
        cd_feedback_st2_temperature=st.session_state.cd_feedback_st2_temperature,
        cd_synthesis_st2_temperature=st.session_state.cd_synthesis_st2_temperature,
        max_iterations=st.session_state.max_iterations,
        approval_threshold=st.session_state.approval_threshold,
        llm_provider=st.session_state.llm_provider,
        llm_model=st.session_state.llm_model,
    )
    _v2_stream(initial_state)


def _v2_run_resume_stream(command: Command) -> None:
    """Resume the paused v2 graph with the user's decision."""
    _v2_stream(command)


def _v2_stream(stream_input) -> None:
    """Drive the stream loop shared by initial and resume calls.

    Per-node events feed ``render_node_progress()`` only. The
    ``__interrupt__`` event is skipped here — the pause is detected
    post-stream via the checkpointer snapshot in
    ``_v2_update_phase_from_graph()``, which is the authoritative
    signal.

    No leading divider — the divider hierarchy is owned by
    ``_render_v2_persistent_brief()``, which sandwiches the brief
    between two dividers and so always provides the separator above
    the streaming section.
    """
    st.markdown("### pipeline executing...")
    for event in agency_graph_st2.stream(stream_input, config=_v2_thread_config()):
        for node_name, node_output in event.items():
            if node_name == "__interrupt__":
                continue
            render_node_progress(node_name, node_output)

    _v2_update_phase_from_graph()


def _render_v2_persistent_brief() -> None:
    """Render the persistent run-context block on the v2 tab.

    Sandwiches a "creative brief" expander (and, once a territory has
    been picked, a "selected territory" expander) between two
    horizontal dividers. Sourced from the checkpointer (not
    session_state) so it survives every rerun for the duration of a
    run's thread_id.

    The selected-territory expander appears directly below the
    creative-brief expander but above the bottom divider — both
    expanders are part of the same persistent context block, so they
    share the dividers rather than each rendering their own. Renders
    nothing (no dividers, no expanders) when there is no thread_id,
    no checkpoint state, or no creative_brief yet — typical on the
    very first script run between the RUN click and the strategist
    completing.
    """
    if not st.session_state.get("v2_thread_id"):
        return
    snap = agency_graph_st2.get_state(_v2_thread_config())
    if not snap.values:
        return
    state = AgencyState.model_validate(snap.values)
    if not state.creative_brief:
        return
    st.markdown("---")
    with st.expander("creative brief", expanded=False):
        st.markdown(state.creative_brief)

    # Selected territory may come from the checkpointer (post-resume,
    # once the interrupt node has set it) or from the session_state
    # preview written at click time in `_render_v2_territory_selection`.
    # The preview lets the expander appear immediately on the next
    # rerun rather than only after the resume stream completes (which
    # is typically at terminal). Checkpointer wins when both are set,
    # so the preview is only the bridge between click and resume-end.
    selected = state.selected_territory
    if selected is None:
        preview = st.session_state.get("v2_selected_territory_preview")
        if preview:
            selected = Territory.model_validate(preview)

    if selected is not None:
        with st.expander(
            f"selected territory · {selected.title}",
            expanded=False,
        ):
            render_territory_body(selected)

    st.markdown("---")


def _render_v2_territory_selection() -> None:
    """Render the territory cards plus selection / rerun controls.

    Reads the paused state from the checkpointer (not from a local
    variable — Streamlit reruns don't preserve locals). Buttons queue
    a pending action and call ``st.rerun()`` so the next run starts
    clean and processes the action at the top of the handler.
    """
    snap = agency_graph_st2.get_state(_v2_thread_config())
    paused_state = AgencyState.model_validate(snap.values)

    if paused_state.status == WorkflowStatus.FAILED:
        render_error_state(paused_state)
        st.markdown("---")
        render_run_metadata(paused_state, mode="v2")
        render_footer()
        return

    # No leading divider — `_render_v2_persistent_brief()` already
    # rendered one below the brief expander, which is directly above
    # this section.
    st.markdown(
        f"### {len(paused_state.territories)} territories — pick one to develop"
    )
    render_territory_cards(paused_state.territories)

    st.markdown("---")
    st.markdown("### select a territory...")

    # One button per territory. Columns mirror the card layout (≤3 cards
    # fit in a single row; 4+ wraps to rows of 3) so the buttons land
    # visually close to their cards even when the grid wraps.
    n = len(paused_state.territories)
    columns_per_row = n if n <= 3 else 3
    for row_start in range(0, n, columns_per_row):
        row = paused_state.territories[row_start : row_start + columns_per_row]
        columns = st.columns(columns_per_row)
        for offset, (column, territory) in enumerate(zip(columns, row)):
            index = row_start + offset
            with column:
                if st.button(
                    f"select {index + 1} · {territory.title}",
                    key=f"v2_select_{index}",
                    use_container_width=True,
                ):
                    st.session_state.v2_pending_action = {
                        "kind": "select",
                        "index": index,
                    }
                    # Preview the selected territory in the persistent
                    # block immediately. The interrupt node sets the
                    # same value into checkpointer state during the
                    # resume stream, but that doesn't surface until
                    # the stream completes (typically at terminal),
                    # which is too late — the user wants visual
                    # confirmation as soon as they click.
                    st.session_state.v2_selected_territory_preview = (
                        territory.model_dump()
                    )
                    st.rerun()

    st.markdown("")
    st.markdown("### ...or regenerate territories")
    rejection_context = st.text_input(
        "steering context (optional) — a short note to nudge the rerun",
        key="v2_rejection_input",
        placeholder="e.g. 'less literal, more provocative' or leave blank",
    )
    if st.button("generate new territories", key="v2_rerun_button"):
        st.session_state.v2_pending_action = {
            "kind": "rerun",
            "context": rejection_context.strip() or None,
        }
        st.rerun()


def _render_v2_terminal() -> None:
    """Render the final output: synthesis, campaign, history, metadata.

    No leading divider — `_render_v2_persistent_brief()` already
    rendered one below the brief expander, which is directly above
    this section.
    """
    snap = agency_graph_st2.get_state(_v2_thread_config())
    final_state = AgencyState.model_validate(snap.values)

    if final_state.status == WorkflowStatus.FAILED:
        render_error_state(final_state)
        st.markdown("---")
        render_run_metadata(final_state, mode="v2")
        render_footer()
        return

    if final_state.status == WorkflowStatus.APPROVED:
        st.success("creative work approved.")
    elif final_state.status == WorkflowStatus.MAX_ITERATIONS_REACHED:
        st.warning(
            "max iterations reached — showing best-of synthesis."
        )

    if final_state.cd_synthesis is not None:
        render_synthesis_output(
            final_state.cd_synthesis,
            final_state.campaign_concept,
        )
    else:
        # Defensive fallback — the v2 graph always produces a synthesis
        # on a non-FAILED terminal path, so this branch is unreachable
        # in normal flow. Kept so the page doesn't crash if the contract
        # breaks.
        st.markdown("### final campaign concept")
        if final_state.campaign_concept is not None:
            st.markdown(f"**{final_state.campaign_concept.title}**")
            st.markdown(final_state.campaign_concept.core_idea)

    st.markdown("---")
    st.markdown("### pipeline history")
    render_history(final_state.history)

    st.markdown("---")
    render_run_metadata(final_state, mode="v2")
    render_footer()


def _render_standard_v2() -> None:
    """Render the Standard 2.0 tab."""
    st.markdown(
        "Submit a client brief and the **standard_st2** pipeline will "
        "generate a set of creative territories for you to pick from, "
        "then develop the one you choose into a full campaign concept."
    )

    brief_text = st.text_area(
        "CLIENT BRIEF",
        height=200,
        value=st.session_state.get("v2_brief_input", ""),
        placeholder=(
            "Describe your brand, target audience, campaign objectives, "
            "channels, budget, and timeline..."
        ),
        key="v2_brief_textarea",
    )

    run_button = st.button(
        "RUN PIPELINE",
        type="primary",
        disabled=not brief_text,
        key="v2_run_button",
    )

    if run_button and brief_text:
        if not check_run_allowed():
            render_run_limit_reached()
            st.stop()
        _reset_v2_session()
        st.session_state.v2_brief_input = brief_text
        st.session_state.v2_thread_id = str(uuid.uuid4())
        st.session_state.v2_pending_action = {"kind": "initial"}
        st.rerun()

    # --- Persistent creative brief widget ---
    # Renders below the RUN button + a divider, sandwiched between two
    # dividers, whenever the strategist has produced a brief. Survives
    # reruns because it sources from the checkpointer on every page
    # render. On the very first script run after RUN (before the
    # strategist has completed) this is a no-op.
    _render_v2_persistent_brief()

    # --- Consume any queued stream action ATOMICALLY at the top. ---
    # `pop` (not `get`) closes the double-consumption window: widget
    # re-renders during the stream could otherwise re-trigger the same
    # action on the next pass.
    pending = st.session_state.pop("v2_pending_action", None)
    if pending is not None:
        kind = pending["kind"]
        if kind == "initial":
            _v2_run_initial_stream(st.session_state.v2_brief_input)
        elif kind == "select":
            _v2_run_resume_stream(
                Command(
                    resume={"action": "select", "index": pending["index"]}
                )
            )
        elif kind == "rerun":
            _v2_run_resume_stream(
                Command(
                    resume={
                        "action": "rerun",
                        "rejection_context": pending["context"],
                    }
                )
            )
        # After every stream end, rerun once so the script restarts
        # cleanly: streaming widgets disappear, the persistent brief
        # widget renders at the top with the now-populated brief, and
        # the appropriate phase UI (territory selection or terminal)
        # renders below it without the streaming-widget clutter.
        st.rerun()

    phase = st.session_state.get("v2_phase", "idle")
    if phase == "interrupted":
        _render_v2_territory_selection()
    elif phase == "terminal":
        _render_v2_terminal()


# ===========================================================================
# Standard 1.0 — original pipeline, unchanged
# ===========================================================================

def _render_standard_v1() -> None:
    """Render the original Standard 1.0 workflow tab.

    Lifted verbatim from the pre-Phase-E workflow page so behaviour
    stays identical. Do not change this function when extending v2 —
    v1 is the untouched baseline.
    """
    st.markdown(
        "Submit a client brief and our **strategist**, **creative** and "
        "**creative director** agents will collaborate to deliver a "
        "creative campaign concept."
    )

    brief_text = st.text_area(
        "CLIENT BRIEF",
        height=200,
        value=st.session_state.get("workflow_brief_input", ""),
        placeholder=(
            "Describe your brand, target audience, campaign objectives, "
            "channels, budget, and timeline..."
        ),
        key="v1_brief_textarea",
    )

    run_button = st.button(
        "RUN PIPELINE",
        type="primary",
        disabled=not brief_text,
        key="v1_run_button",
    )

    # -----------------------------------------------------------------
    # Pipeline execution with live progress
    # -----------------------------------------------------------------

    if run_button and brief_text:
        if not check_run_allowed():
            render_run_limit_reached()
            st.stop()
        st.session_state.workflow_brief_input = brief_text
        # Clear any cached final state so a mid-stream crash that fails
        # to accumulate updates doesn't leave the prior run rendered.
        st.session_state.pop("workflow_result", None)
        graph = build_graph_st1()

        initial_state = AgencyState(
            client_brief=brief_text,
            strategist_st1_strategic_philosophy=st.session_state.strategist_st1_strategic_philosophy,
            creative_st1_creative_philosophy=st.session_state.creative_st1_creative_philosophy,
            creative_director_st1_creative_philosophy=st.session_state.creative_director_st1_creative_philosophy,
            max_iterations=st.session_state.max_iterations,
            approval_threshold=st.session_state.approval_threshold,
            llm_provider=st.session_state.llm_provider,
            llm_model=st.session_state.llm_model,
        )

        progress_container = st.container()

        with progress_container:
            st.markdown("---")
            st.markdown("### pipeline executing...")

            # LangGraph's stream yields per-node dict updates. We
            # accumulate them into a running dict and then rehydrate to
            # an AgencyState at the end so downstream code can use
            # attribute access and typed nested models.
            accumulated: dict = {}

            for event in graph.stream(initial_state):
                for node_name, node_output in event.items():
                    render_node_progress(node_name, node_output)
                    accumulated.update(node_output)

            if accumulated:
                st.session_state.workflow_result = AgencyState.model_validate(
                    accumulated
                )

        # After streaming completes, rerun once so the script restarts
        # cleanly — streaming widgets disappear and the persisted
        # result renders alone below the brief input. The user can use
        # pipeline history below the recommendation to inspect each
        # iteration in detail.
        st.rerun()

    # -----------------------------------------------------------------
    # Render persisted result (survives page switches)
    # -----------------------------------------------------------------

    if "workflow_result" in st.session_state:
        final_state = st.session_state.workflow_result

        st.markdown("---")

        if final_state.status == WorkflowStatus.FAILED:
            render_error_state(final_state)
            st.markdown("---")
            render_run_metadata(final_state, mode="v1")
            render_footer()
        else:
            if final_state.status == WorkflowStatus.APPROVED:
                st.success("creative work approved.")
            elif final_state.status == WorkflowStatus.MAX_ITERATIONS_REACHED:
                st.warning(
                    "max iterations reached — showing best scoring idea."
                )

            st.markdown("### final creative concept")
            st.markdown(final_state.creative_concept or "")

            st.markdown("---")
            st.markdown("### pipeline history")
            render_history(final_state.history)

            st.markdown("---")
            render_run_metadata(final_state, mode="v1")

            render_footer()


# ---------------------------------------------------------------------------
# Tab dispatch
# ---------------------------------------------------------------------------

with tab_v2:
    _render_standard_v2()

with tab_v1:
    _render_standard_v1()
