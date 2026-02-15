# ADR 0004: Structured Output for Creative Director Evaluation

**Status:** Accepted  
**Date:** 2026-02-15

## Context

The Creative Director agent must return a structured evaluation containing a numeric score, strengths, weaknesses, and actionable direction. This evaluation drives the conditional routing in the graph — the score is compared against the approval threshold to decide whether to approve or loop back for revision.

Alternatives considered:

- **Freeform text with parsing** — ask the LLM to respond naturally, then extract the score via regex or a second LLM call. Fragile, error-prone, and adds latency.
- **JSON mode with manual validation** — ask the LLM to return JSON and parse it manually. Better than freeform but no schema enforcement at the LLM level.
- **Pydantic structured output** — pass a `CDEvaluation` Pydantic model to `with_structured_output()`. The LLM is constrained to return valid JSON matching the schema, and Pydantic validates it automatically.

## Decision

Use **Pydantic structured output** via LangChain's `with_structured_output(CDEvaluation)` for the Creative Director agent.

## Consequences

- **Positive:** The score is guaranteed to be a float between 0 and 100. The conditional routing logic is a simple numeric comparison with no parsing.
- **Positive:** Strengths and weaknesses are returned as typed lists, making them easy to display in the frontend and log in history.
- **Positive:** The same `CDEvaluation` model used for validation is also used for state storage and history — no translation layer.
- **Negative:** Structured output constrains the LLM's response format, which may slightly reduce the naturalness of feedback compared to freeform text. Mitigated by the `direction` field which allows open-ended guidance.
- **Negative:** Not all providers support structured output equally well. Requires testing across Anthropic, Google, and OpenAI to ensure consistent behaviour.
