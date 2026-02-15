# ADR 0005: Streamlit for Frontend Interface

**Status:** Accepted  
**Date:** 2026-02-15

## Context

agt_sea needs a simple frontend that allows users to submit a client brief, select a creative philosophy, observe the agent workflow in progress, and view the final creative output along with iteration history.

Requirements for v1:

- Fast to build — the frontend is not the core of the project
- Python-native — avoids context-switching to a separate JS/TS stack
- Supports real-time updates as agents execute
- Can display structured data (evaluation scores, history)

Alternatives considered:

- **Chainlit** — purpose-built for LLM chat interfaces with built-in streaming and step visualisation. Strong fit but more opinionated and less flexible for custom layouts.
- **Gradio** — similar to Streamlit but more focused on ML model demos. Less suited to multi-step workflow visualisation.
- **React / Next.js** — maximum flexibility but requires a separate frontend codebase, API layer, and JS/TS knowledge. Overkill for v1.

## Decision

Use **Streamlit** for the v1 frontend.

## Consequences

- **Positive:** Python-native, so the entire project stays in one language. Fast iteration — a working UI in hours, not days.
- **Positive:** Built-in components for forms (brief input, philosophy selector), progress indicators, and structured data display (tables, expanders for history).
- **Positive:** `st.status` and `st.expander` map naturally to showing agent progress through the graph.
- **Negative:** Limited customisation compared to a full frontend framework. Acceptable for v1.
- **Negative:** Streamlit's execution model (full re-run on interaction) can be unintuitive. Requires care with session state management.
- **Note:** A migration to a more polished frontend (e.g., React) remains an option for a future phase if the project warrants it.
