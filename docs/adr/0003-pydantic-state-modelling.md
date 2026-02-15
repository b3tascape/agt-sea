# ADR 0003: Pydantic for State and Data Modelling

**Status:** Accepted  
**Date:** 2026-02-15

## Context

The agent graph requires a shared state object that flows between nodes. This state must be well-defined, validated, and self-documenting. It also needs to support structured output from LLM calls (see ADR 0004).

Alternatives considered:

- **Plain dictionaries** — flexible but no validation, no autocomplete, no documentation. Typos in keys cause silent bugs.
- **Python dataclasses** — typed and lightweight but lack built-in validation, serialisation, and the `Field()` metadata that Pydantic provides.
- **TypedDict** — LangGraph's native state convention. Lightweight but no runtime validation. May be used as a thin wrapper over Pydantic models at the graph level.

## Decision

Use **Pydantic `BaseModel`** for all data models (`AgencyState`, `CDEvaluation`, `AgentOutput`). Adapt to LangGraph's `TypedDict` convention at the graph boundary where needed.

## Consequences

- **Positive:** Runtime validation catches malformed state early. `Field()` constraints (e.g., `ge=0, le=100` on scores) enforce business rules at the data layer.
- **Positive:** Models double as structured output schemas for LLM calls via `with_structured_output()`.
- **Positive:** Self-documenting — descriptions on every field serve as inline documentation.
- **Positive:** Serialisation to/from JSON is built in, useful for logging, debugging, and frontend display.
- **Negative:** Slight overhead compared to plain dicts or TypedDicts. Negligible for this use case.
