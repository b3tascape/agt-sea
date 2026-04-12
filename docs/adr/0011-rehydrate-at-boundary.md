# ADR 0011: Rehydrate LangGraph Output to Pydantic at the Boundary

**Status:** Accepted
**Date:** 2026-04-08
**Refines:** [ADR 0003](0003-pydantic-state-modelling.md) (the "adapt to TypedDict at the graph boundary" note)

## Context

ADR 0003 chose Pydantic `BaseModel` as the data layer for `AgencyState`, `CDEvaluation`, and `AgentOutput`. It noted in passing that the project would "adapt to LangGraph's `TypedDict` convention at the graph boundary where needed." In practice, this caveat became a real friction point.

LangGraph accepts a Pydantic model as input to `graph.invoke()` and `graph.stream()`, but the object it returns (and the per-node updates yielded by `stream()`) are plain Python dicts, not Pydantic models. This is an artefact of how LangGraph's internal reducer and checkpointer machinery represents state. The consequences for downstream code:

- Frontend pages and tests had to use `final_state.get("status")` and `final_state["history"]` instead of attribute access.
- All static typing benefits vanished at the most important boundary — the one where untyped consumer code starts working with the result.
- Nested models lost their typing too. `final_state["history"][0]` was a dict, not an `AgentOutput`. `final_state["cd_evaluation"]["score"]` was a raw number, not a validated `CDEvaluation.score`.
- `.get()` could silently return `None` where a Pydantic attribute access would have raised `AttributeError` — turning loud failures into quiet bugs.
- Enum values (e.g. `WorkflowStatus.APPROVED`) lost their enum type and became plain strings.

The pattern was documented as a known gotcha in CLAUDE.md and deferred to Phase 6 for resolution. This ADR captures the decision made when the work was done.

Alternatives considered:

- **Live with dicts (the original ADR 0003 caveat).** Every consumer of graph output uses `.get()` and dict indexing. Verbose, error-prone, loses all typing benefits at the boundary. The status quo until this ADR.
- **Refactor `AgencyState` to use a `TypedDict` instead of a Pydantic model.** Aligns the data model with LangGraph's internal convention, eliminating the boundary entirely. But sacrifices Pydantic's runtime validation, `Field()` constraints, default factories, and structured-output integration with `with_structured_output()` — all of which ADR 0003 explicitly chose Pydantic *for*. A non-starter.
- **Wait for LangGraph to fix this upstream.** LangGraph 1.x may at some point return Pydantic models directly when constructed with `StateGraph(AgencyState)`. Possible but not guaranteed, and the project couldn't be blocked indefinitely on a hypothetical upstream change.
- **Rehydrate at the boundary.** Convert the dict back into a Pydantic model the moment it crosses out of LangGraph, using `AgencyState.model_validate(raw)`. One line, once, per consumer. Everything downstream uses attribute access and full typing.

## Decision

Every consumer of LangGraph output rehydrates the result back into `AgencyState` using `AgencyState.model_validate()` immediately after the graph call. Downstream code uses attribute access exclusively — no `.get()`, no `["field"]`.

For `graph.invoke()`, the pattern is straightforward:

```python
raw = agency_graph.invoke(initial_state)
final_state = AgencyState.model_validate(raw)
# downstream code uses final_state.status, final_state.history[0].evaluation.score, etc.
```

For `graph.stream()`, which yields per-node dict updates rather than full state snapshots, accumulate the updates into a running dict and rehydrate once at the end. Do not assume the last event contains the full state — it doesn't.

```python
accumulated: dict = {}
for event in graph.stream(initial_state):
    for node_name, node_output in event.items():
        render_node_progress(node_name, node_output)
        accumulated.update(node_output)

if accumulated:
    final_state = AgencyState.model_validate(accumulated)
```

The canonical examples live in `frontend/pages/workflow.py` (streaming case) and `tests/test_pipeline.py` (invoke case). Both are referenced from CLAUDE.md's Architecture Rules section as the patterns new code should follow.

Inside agent functions — which run *before* state crosses the LangGraph boundary — attribute access already works on the Pydantic model passed in. No rehydration is needed there. This ADR concerns only the consumer-side boundary.

## Consequences

- **Positive:** Full Pydantic typing is restored at exactly the place it matters most: where consumer code starts working with results. Attribute access, autocomplete, runtime validation, enum coercion, and nested model typing all work as ADR 0003 intended.
- **Positive:** Loud failures replace quiet ones. A typo like `final_state.statsu` raises `AttributeError` immediately; the previous `final_state.get("statsu")` returned `None` and propagated as a confusing `NoneType` error several lines later.
- **Positive:** Centralised contract. CLAUDE.md documents the pattern in one place, and `model_validate()` is the single point where any future schema validation issues will surface — easy to debug.
- **Positive:** Forward-compatible with checkpointing. LangGraph's checkpointers serialise state to disk as dicts; rehydrating on retrieval is the same pattern. Phase 6.1 (human-in-the-loop with interrupt/resume) will use this same approach when reading state back from a checkpoint.
- **Positive:** The streaming pattern (`accumulated.update`) makes explicit the otherwise non-obvious fact that `stream()` events are *partial updates*, not snapshots. Any developer extending the streaming logic now has a working reference rather than a trap.
- **Negative:** Requires discipline. Every new consumer of graph output must remember to rehydrate. Easy to forget and accidentally use dict access on the raw return value, which would silently regress the typing benefits. Mitigated by the CLAUDE.md rule, the canonical examples, and the fact that any attribute access on the un-rehydrated dict will fail loudly at the first call site.
- **Negative:** A small validation cost on every graph call (one Pydantic `model_validate` pass). Negligible at the project's current scale and dwarfed by LLM call latency. Not a concern.
- **Negative:** Doesn't help upstream code that wants to operate on partial state during streaming. The progress renderer still receives raw dict events and reads them positionally. Acceptable — the progress renderer only needs a handful of known fields and doesn't benefit from full rehydration on every event.
- **Neutral:** This ADR refines ADR 0003 rather than superseding it. The Pydantic-as-state-layer decision is unchanged; only the boundary handling is now explicit. ADR 0003's status line has been updated to flag the refinement, per the project's append-only ADR convention.
