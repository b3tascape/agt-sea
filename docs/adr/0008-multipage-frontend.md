# ADR 0008: Multipage Frontend Architecture

**Status:** Accepted (backfilled)
**Date:** 2026-04-07

## Context

The original frontend was a single-page Streamlit app that exposed only the full creative campaign workflow. As the project grew, two needs emerged:

1. **Standalone access to individual agents.** Users wanted to run the strategist or creative agent on its own without invoking the full pipeline — for example, to iterate on a creative brief in isolation, or to feed an externally-written brief into the creative agent directly.
2. **Room for future modules.** The roadmap includes Tools, Marketing, Production, and other modules that don't fit inside a single-workflow frame. The frontend needed a structure that could host independent modules without each one polluting the others' code or state.

A single `app.py` file handling everything was already showing strain — global parameter widgets, page-specific logic, and shared rendering helpers were all tangled together. Splitting concerns was overdue.

Alternatives considered:

- **Keep single-page, use `st.tabs()` for module separation.** Lightweight but tabs don't survive reruns cleanly, can't be deep-linked, and don't scale to more than a handful of modules. Also conflates "this is a separate module" with "this is a sub-view of one module."
- **Multiple Streamlit apps deployed independently.** Maximum isolation but multiplies deployment complexity, splits the sidebar/global state, and breaks the unified product experience.
- **Streamlit `st.navigation()` with `st.Page()` (multipage app).** Native multipage support introduced in recent Streamlit versions. Pages are separate files, share session state and sidebar, and have proper URL routing.

## Decision

Restructure the frontend as a multipage Streamlit app using `st.navigation()` and `st.Page()`. The structure is:

- **`frontend/app.py`** — navigation shell only. Page config, theme loading, sidebar rendering, page registration, routing. No page-specific content.
- **`frontend/pages/`** — one file per module. Each page file is a self-contained Streamlit script that can read from `st.session_state` (populated by the sidebar) and call agents directly.
- **`frontend/components/`** — shared UI components (sidebar, agent_output, history, run_metadata, progress, footer, labels). Importable from any page.
- **`frontend/themes/`** — CSS and assets, loaded once by `app.py`.

Pages registered via `st.navigation()` are visible in the sidebar nav. Pages that exist but are not registered (placeholders for future modules) can be added without making them user-visible.

Sidebar global parameters (philosophy selectors, LLM provider/model, iterations, threshold) are written to `st.session_state` once per render and read by every page. This is the mechanism by which user choices flow into agent invocations regardless of which page is active.

## Consequences

- **Positive:** Each page is independently developable. Adding a new module is "create a new file in `pages/` and register it in `app.py`" — no risk of breaking other modules.
- **Positive:** Clean separation of concerns. Components are reusable across pages without copy-paste. The sidebar is rendered once and its state flows everywhere.
- **Positive:** Standalone agent pages (Strategy, Creative) can call agent functions directly without going through the LangGraph workflow, which is the right model for single-shot agent runs.
- **Positive:** Placeholder pages can exist in the codebase without being user-visible, making it easy to scaffold future modules without committing to a release date.
- **Positive:** URL routing works correctly — users can deep-link to specific pages and the browser back button behaves as expected.
- **Negative:** `frontend/app.py` requires a `sys.path.insert` at the top to make the `agt_sea` package importable when run from the project root. This is a Streamlit Cloud deployment requirement, not a local-dev one, and is documented in CLAUDE.md.
- **Negative:** Page files run in the same Python process as `app.py`, which means they share imports and module state. This is convenient but means a buggy page can affect others — discipline is required.
- **Negative:** Streamlit's session state persists across page navigations but resets on hard reload. Pages that hold expensive results (like a completed pipeline run) need explicit `st.session_state` storage to survive tab switches. Handled per-page rather than centrally.
