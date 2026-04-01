# SPEC: Multipage Streamlit Application

**Status:** Draft
**Date:** 2026-03-30
**Scope:** Restructure `frontend/app.py` from a single-page Streamlit app into a multipage application using `st.navigation()` / `st.Page()`.

---

## 1. Goals

- Break the monolithic `app.py` into one page file per module
- Enable independent development of new modules without touching existing pages
- Extract reusable UI components and theme CSS into shared directories
- Placeholder modules exist in code but do not appear in the running app (except Tools, which is visible with a holding message)

**Backend changes required** (minimal — no new directories under `src/`):
- `state.py`: make `client_brief` optional (default `""`), update `max_iterations` default to 3, update `approval_threshold` default to 80.0
- `config.py`: update `DEFAULT_MODELS` to local/development tier, replace single `MODEL_NAME` secret with per-provider secrets (`ANTHROPIC_MODEL`, `GOOGLE_MODEL`, `OPENAI_MODEL`), update `MAX_ITERATIONS` default to 3, update `APPROVAL_THRESHOLD` default to 80.0
- `provider.py`: add `model` parameter to `get_llm()` so the sidebar model selector can override the config default

---

## 2. Navigation Architecture

### Approach: Explicit `st.navigation()`

We use `st.navigation()` with `st.Page()` objects defined in `app.py` — **not** the auto-discovery `pages/` convention. This gives us explicit control over page order, labels, and which pages are visible.

```python
# app.py — simplified
pages = [
    st.Page("pages/strategy.py", title="Strategy"),
    st.Page("pages/creative.py", title="Creative"),
    st.Page("pages/workflow.py", title="Workflow"),
    st.Page("pages/tools.py", title="Tools"),
]
pg = st.navigation(pages)
pg.run()
```

**Why explicit registration?** The auto-discovery convention (`pages/` directory scanned alphabetically) gives us no control over ordering, naming, or conditional visibility. With `st.navigation()`, we choose exactly which pages appear and in what order. Placeholder files sit in `pages/` but are never passed to `st.navigation()`, so they are invisible to users.

### Visible modules (in sidebar order)

| Sidebar label | File | Description |
|---|---|---|
| Strategy | `pages/strategy.py` | Standalone strategist — client brief in, creative brief out |
| Creative | `pages/creative.py` | Standalone creative — creative brief in, concepts out |
| Workflow | `pages/workflow.py` | Full pipeline (current app moved here), tabbed for future workflows |
| Tools | `pages/tools.py` | Visible with "in development" holding message, `--accent-aquagreen` theme |

### Placeholder modules (files exist, not registered)

| Module | File | Purpose |
|---|---|---|
| Marketing | `pages/marketing.py` | Future: client brief writing |
| Production | `pages/production.py` | Future: image/audio/film/social content |
| Agnostic | `pages/agnostic.py` | Future: TBC |

**Activation:** When a placeholder is ready, add its `st.Page()` call to the `pages` list in `app.py`. No other wiring needed.

---

## 3. Sidebar Layout

The sidebar is divided into two sections, top to bottom:

```
┌─────────────────────────┐
│  { agt_sea }            │  ← Logo / title
│─────────────────────────│
│  Strategy               │  ← st.navigation() renders
│  Creative               │     page links here
│  Workflow                │     automatically
│  Tools                  │
│─────────────────────────│
│  CREATIVE PHILOSOPHY    │  ← Global parameters
│  [bold & disruptive ▾]  │     (below nav, separated
│                         │      by divider)
│  LLM PROVIDER           │
│  [anthropic ▾]          │
│                         │
│  LLM MODEL              │
│  [claude-sonnet-4-6 ▾]  │
│                         │
│  MAX ITERATIONS         │
│  [3]                    │
│                         │
│  APPROVAL THRESHOLD     │
│  [80]                   │
│─────────────────────────│
│                 SM λ ©  │  ← Footer
└─────────────────────────┘
```

### Global parameters

All global parameters live in the sidebar, below the navigation links. They are rendered once in `app.py` (or via a shared sidebar component) and stored in `st.session_state` so every page can read them.

| Parameter | Widget | Default | Session state key | Notes |
|---|---|---|---|---|
| Creative Philosophy | `selectbox` | Bold & Disruptive | `creative_philosophy` | |
| LLM Provider | `selectbox` | Anthropic | `llm_provider` | Only providers with a valid API key are selectable (see below) |
| LLM Model | `selectbox` | `get_model_name(provider)` | `llm_model` | Options change dynamically when provider changes (see below) |
| Max Iterations | `number_input` | 3 | `max_iterations` | Range: 1–5 |
| Approval Threshold | `number_input` | 80 | `approval_threshold` | |

**Why global?** These parameters affect multiple modules. Creative philosophy shapes the workflow's CD evaluation and could influence future standalone CD pages. LLM provider and model apply everywhere. Iterations and threshold are workflow-specific today but live in the global section for simplicity — this can be revisited if per-page params emerge.

**How pages read them:** Each page reads from `st.session_state` (e.g., `st.session_state.creative_philosophy`). This decouples sidebar rendering from page logic.

### Provider availability

Not all users have API keys for every provider. The provider selector only enables providers whose API key is present and non-empty:

```python
# Check which providers have valid keys
available = {
    LLMProvider.ANTHROPIC: bool(os.environ.get("ANTHROPIC_API_KEY")),
    LLMProvider.GOOGLE: bool(os.environ.get("GOOGLE_API_KEY")),
    LLMProvider.OPENAI: bool(os.environ.get("OPENAI_API_KEY")),
}
```

Providers without a valid key are greyed out and not selectable. The default provider is the first available one (Anthropic if its key exists, otherwise Google, otherwise OpenAI).

### Model selector

The model dropdown updates dynamically when the provider changes. Available models per provider:

| Provider | Models |
|---|---|
| Anthropic | `claude-haiku-4-5-20251001`, `claude-sonnet-4-6`, `claude-opus-4-6` |
| Google | `gemini-3.1-flash-lite-preview`, `gemini-3-flash-preview`, `gemini-3.1-pro-preview` |
| OpenAI | `gpt-5.4-nano`, `gpt-5.4-mini`, `gpt-5.4` |

The model selector defaults to whatever `get_model_name(provider)` returns for the active provider, which respects Streamlit Cloud secrets (cost-controlled tier) or falls back to `DEFAULT_MODELS` (local/development tier). The user can change the model during the session.

If the provider is greyed out (no valid key), its model selector is also greyed out and not selectable.

### Per-page (local) parameters

None defined yet. When a module needs its own parameters, it renders them in the main content area of that page (not the sidebar), using a clearly labelled section. The spec will be updated when local params are introduced.

---

## 4. Module Specifications

### 4.1 Strategy (Module 02) — `pages/strategy.py`

**Purpose:** Standalone strategist. User provides a client brief, gets a structured creative brief.

**Backend call:** `run_strategist()` directly — no LangGraph.

**Flow:**
1. Page title + description (what this module does, moved from old sidebar copy)
2. Text area: user enters client brief
3. "Run Strategist" button
4. On run: construct `AgencyState(client_brief=...)`, call `run_strategist(state)`
5. Display result: creative brief content + agent metadata (provider, model, timestamp)

**Why no LangGraph?** A single agent call doesn't need an orchestration framework. `run_strategist()` already encapsulates the full agent logic — prompt construction, LLM call, state update. Calling it directly is simpler, faster, and avoids unnecessary graph overhead.

### 4.2 Creative (Module 03) — `pages/creative.py`

**Purpose:** Standalone creative. User provides a creative brief, gets three campaign concepts.

**Backend call:** `run_creative()` directly — no LangGraph, no CD loop.

**Flow:**
1. Page title + description
2. Text area: user enters a creative brief (manually written or copied from Strategy page)
3. "Run Creative" button
4. On run: construct `AgencyState(creative_brief=<user input>)`, call `run_creative(state)`
5. Display result: creative concepts + agent metadata

**Single-shot only.** No iteration loop, no Creative Director feedback. The standalone creative page is a one-pass tool. The iterative loop with CD evaluation lives in the Workflow module.

**No handoff from Strategy page.** The two standalone pages are independent — users copy/paste between them manually. Automated handoff is a future enhancement.

**Backend change:** `client_brief` becomes optional on `AgencyState` (default `""`). This avoids every standalone page needing to pass an awkward empty string for a field the agent doesn't read. See Section 1.

### 4.3 Workflow (Module 06) — `pages/workflow.py`

**Purpose:** The current full pipeline (Strategist → Creative → CD loop) moved here, with a tab structure for future workflows.

**Backend call:** `build_graph()` + `graph.stream()` via LangGraph — same as current `app.py`.

**Tab structure (scaffolded now):**

```python
tab_campaign, = st.tabs(["Creative Campaign"])

with tab_campaign:
    # Current pipeline UI lives here (moved from app.py)
    ...
```

**Why scaffold tabs now?** Adding a second tab later means restructuring the page layout. Scaffolding the single-tab structure now means the second workflow just adds another tab name and `with` block — no layout refactor needed.

**Flow (within "Creative Campaign" tab):**
1. Brief description of the workflow
2. Text area: client brief input
3. "Run Pipeline" button
4. Live progress display (streaming status containers)
5. Results: final concept, pipeline history (expanders), run metadata

This is the existing `app.py` logic, moved wholesale into the tab.

### 4.4 Tools (Module 07) — `pages/tools.py`

**Visible in navigation** with `--accent-aquagreen` theme applied. Content is a holding message only:

```python
"""agt_sea — Tools"""

import streamlit as st

# Apply accent theme override
st.markdown("""
<style>
    .stApp { background-color: var(--accent-aquagreen) !important; }
    section[data-testid="stSidebar"] { background-color: var(--accent-aquagreen) !important; }
</style>
""", unsafe_allow_html=True)

st.title("Tools")
st.info("This module is in development.")
```

Further Tools development is out of scope for this spec.

### 4.5 Hidden placeholder modules

Each hidden placeholder file follows the same minimal pattern:

```python
"""agt_sea — [Module Name] (placeholder)"""

import streamlit as st

st.title("[Module Name]")
st.info("This module is under development.")
```

These files exist so the module structure is visible in the codebase, but they are never registered in `st.navigation()` and are therefore invisible to users.

Placeholder modules: Marketing (`pages/marketing.py`), Production (`pages/production.py`), Agnostic (`pages/agnostic.py`).

---

## 5. Shared Components

Reusable UI elements extracted from existing code in `app.py` to `frontend/components/`. Each component is a Python module exposing one or more functions that render Streamlit widgets. These are not newly written — each proposed component corresponds to an existing inline block in the current `app.py`, extracted as a reusable function.

### Proposed components

| File | Function(s) | Used by | Purpose |
|---|---|---|---|
| `agent_output.py` | `render_agent_output(entry: AgentOutput)` | Strategy, Creative, Workflow | Displays a single agent output: metadata row (provider, model, timestamp) + content. For CD outputs, also renders score, strengths, weaknesses, direction. |
| `history.py` | `render_history(history: list[AgentOutput])` | Workflow | Renders the full pipeline history as a sequence of labelled expanders, each containing a `render_agent_output()` call. |
| `run_metadata.py` | `render_run_metadata(state: dict)` | Workflow | The metrics row at the bottom: iterations, history count, philosophy, status. |
| `progress.py` | `render_node_progress(node_name, node_output)` | Workflow | Live streaming status container for a single graph node during execution. |
| `footer.py` | `render_footer()` | All pages | The `SM λ ©` badge. |
| `sidebar.py` | `render_sidebar()` | `app.py` | Logo, global parameters, footer. Writes to `st.session_state`. |

**Why extract these?** The Strategy and Creative pages both need to display agent output with metadata — that's `render_agent_output()`. The Workflow page uses all components. Without extraction, we'd duplicate the metadata column layout and CD evaluation rendering across three files.

**What stays page-specific:** Input forms, page titles/descriptions, the pipeline streaming orchestration loop, tab structure. These are unique to each page and don't benefit from abstraction.

### Component design principles

- Each function takes data in, renders widgets, returns nothing
- No component reads `st.session_state` directly — the caller passes what's needed (exception: `render_sidebar()` which is the component that *writes* to session state)
- Components don't import from each other (flat hierarchy) except `history.py` calling `render_agent_output()`

---

## 6. Theme System

### Single CSS file with CSS custom properties

All theme CSS moves from inline in `app.py` to `frontend/themes/b3ta.css`. It is loaded once in `app.py` via `st.markdown()` and applies to all pages.

```
frontend/themes/
└── b3ta.css              # The single theme file
```

### Colour palette

The CSS `:root` block defines all colours, including secondary/accent colours that are not applied by default but are available for specific modules:

```css
:root {
    /* --- Primary palette (applied globally) --- */
    --chartreuse: #eeff41;
    --dark: #333333;
    --dark-grey: #000000;
    --mid-grey: #979797;
    --light-grey: #d9d9d9;
    --white: #fafafa;

    /* --- Secondary / accent palette (defined, not applied by default) --- */
    --accent-aquagreen: #71F7B7;
    --accent-coral: #ff7e79;
    /* Additional accent colours can be added here as needed */
}
```

**How a page applies secondary colours:** A page like Tools injects a small CSS override via `st.markdown()` that remaps the primary colour:

```python
# In pages/tools.py
st.markdown("""
<style>
    .stApp { background-color: var(--accent-aquagreen) !important; }
    section[data-testid="stSidebar"] { background-color: var(--accent-aquagreen) !important; }
    /* ... other overrides as needed ... */
</style>
""", unsafe_allow_html=True)
```

**Why a single file with overrides?** Maintaining two full theme files means duplicating ~350 lines of CSS and keeping them in sync. A single file with a small per-page override is easier to maintain. The secondary colours are defined in `:root` so they're available to any page without re-declaring them.

### Theme loading

```python
# app.py
from pathlib import Path

theme_css = (Path(__file__).parent / "themes" / "b3ta.css").read_text()
st.markdown(f"<style>{theme_css}</style>", unsafe_allow_html=True)
```

---

## 7. File Structure

### Target state

```
frontend/
├── app.py                      # Entry point: st.set_page_config, theme loading,
│                                #   st.navigation(), sidebar rendering
├── pages/
│   ├── marketing.py            # Module 01 — placeholder (not registered)
│   ├── strategy.py             # Module 02 — standalone strategist
│   ├── creative.py             # Module 03 — standalone creative
│   ├── production.py           # Module 04 — placeholder (not registered)
│   ├── agnostic.py             # Module 05 — placeholder (not registered)
│   ├── workflow.py             # Module 06 — full pipeline (tabbed)
│   └── tools.py                # Module 07 — visible with holding message
├── components/
│   ├── agent_output.py         # Single agent output display
│   ├── history.py              # Pipeline history (list of expanders)
│   ├── run_metadata.py         # Run metrics bar
│   ├── progress.py             # Live node progress container
│   ├── footer.py               # Footer badge
│   └── sidebar.py              # Logo + global params + footer
└── themes/
    └── b3ta.css                # Theme CSS (single file)
```

### Backend — changes

```
src/agt_sea/
├── agents/                     # Shared agents — called by standalone pages AND workflows
│   ├── strategist.py           # No changes
│   ├── creative.py             # No changes
│   └── creative_director.py    # No changes
├── graph/workflow.py           # No changes — used by Workflow page only
├── llm/provider.py             # Add model parameter to get_llm() (see Section 9 for full signature)
├── models/state.py             # client_brief optional, update defaults
└── config.py                   # Per-provider model secrets, update defaults
```

**Why keep agents in `src/`?** Agents are backend logic — prompt construction, LLM calls, state management. They are building blocks shared across multiple frontend pages and used by integration tests. Moving them closer to the frontend would break this separation.

---

## 8. `app.py` Responsibilities

The entry point handles everything that must run once, before any page:

1. **`sys.path` hack** — for Streamlit Cloud import resolution (existing behaviour). **Page files also depend on this** — since `st.Page()` loads pages within the same process, the `sys.path` modification in `app.py` is already in effect when page code runs. This is the mechanism that allows `from agt_sea.agents.strategist import run_strategist` to work inside `pages/strategy.py`.
2. **`st.set_page_config()`** — must be the first Streamlit command, called once
3. **Theme CSS loading** — read `b3ta.css`, inject via `st.markdown()`
4. **Sidebar rendering** — logo, global params (writes to `st.session_state`), footer
5. **Page registration** — `st.navigation()` with visible modules only
6. **`pg.run()`** — hands off to the selected page

```python
# app.py — structural outline
import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

st.set_page_config(page_title="agt_sea", page_icon="🌊", layout="wide")

# Load and inject theme
theme_css = (Path(__file__).parent / "themes" / "b3ta.css").read_text()
st.markdown(f"<style>{theme_css}</style>", unsafe_allow_html=True)

# Sidebar: logo + global params
# Note: render_sidebar() imports os internally to check API key
# availability for provider greying-out logic (see Section 3)
from components.sidebar import render_sidebar
render_sidebar()

# Navigation
pages = [
    st.Page("pages/strategy.py", title="Strategy"),
    st.Page("pages/creative.py", title="Creative"),
    st.Page("pages/workflow.py", title="Workflow"),
    st.Page("pages/tools.py", title="Tools"),
]
pg = st.navigation(pages)
pg.run()
```

**Note on imports:** Streamlit runs `app.py` from the `frontend/` directory. Component imports within `frontend/` use direct imports from that working directory (e.g., `from components.sidebar import render_sidebar`), **not** `from frontend.components.sidebar`. The same pattern applies to all component imports within page files. Backend imports use the `agt_sea.*` namespace (e.g., `from agt_sea.agents.strategist import run_strategist`), resolved via the `sys.path` hack.

---

## 9. Session State Contract

Global parameters are written to `st.session_state` by `render_sidebar()` and read by pages. This is the agreed contract:

| Key | Type | Default | Set by |
|---|---|---|---|
| `creative_philosophy` | `CreativePhilosophy` | `BOLD_AND_DISRUPTIVE` | `render_sidebar()` |
| `llm_provider` | `LLMProvider` | First available provider | `render_sidebar()` |
| `llm_model` | `str` | `get_model_name(provider)` | `render_sidebar()` |
| `max_iterations` | `int` | `3` | `render_sidebar()` |
| `approval_threshold` | `float` | `80.0` | `render_sidebar()` |

**Pages must not write to these keys.** They are owned by the sidebar. Pages read them to construct state or configure behaviour.

### LLM provider bridging

Pages pass the selected provider and model directly to `get_llm()`:

```python
llm = get_llm(
    provider=st.session_state.llm_provider,
    model=st.session_state.llm_model,
)
```

The updated `get_llm()` signature:

```python
def get_llm(
    provider: LLMProvider | None = None,
    model: str | None = None,
    temperature: float = 0.7,
) -> BaseChatModel:
```

Logic: if `model` is passed, use it directly as the model name; if `model` is `None`, call `get_model_name(provider)` as before. This means existing callers (agents, tests) that don't pass `model` continue to work unchanged — only frontend pages pass the explicit model from session state.

`config.py`'s environment variable lookup remains as the fallback for non-frontend contexts (tests, CLI scripts) where no session state exists.

### Model selection

Two model tiers exist:

**Cloud defaults (Streamlit Cloud — cost control):**
- Anthropic: `claude-haiku-4-5-20251001`
- Google: `gemini-3.1-flash-lite-preview`
- OpenAI: `gpt-5.4-nano`

**Local defaults (development — mid-tier):**
- Anthropic: `claude-sonnet-4-6`
- Google: `gemini-3-flash-preview`
- OpenAI: `gpt-5.4-mini`

**Implementation — `config.py` changes:**
- `DEFAULT_MODELS` is updated to the local/development tier models
- The single `MODEL_NAME` secret is replaced with per-provider secrets: `ANTHROPIC_MODEL`, `GOOGLE_MODEL`, `OPENAI_MODEL`
- A `_PROVIDER_MODEL_KEYS` mapping connects each `LLMProvider` to its secret name
- `get_model_name(provider)` checks for the provider-specific secret first, then falls back to `DEFAULT_MODELS[provider]`
- Streamlit Cloud secrets dashboard sets `ANTHROPIC_MODEL=claude-haiku-4-5-20251001`, etc.

Pages pass the selected provider to `get_llm(provider=..., model=...)` and the sidebar model selector defaults to whatever `get_model_name(provider)` returns — so Cloud gets cost-controlled defaults, local gets mid-tier defaults, and the user can override during the session.

---

## 10. Deployment Considerations

- **Streamlit Cloud entry point** stays as `frontend/app.py` — no change to the deployment config
- **`sys.path` hack** remains in `app.py` for Streamlit Cloud import resolution — page files depend on it too (see Section 8)
- **API keys** continue to flow through `config.py` → `_get_secret()` → `st.secrets` bridge
- **Per-provider model secrets** (`ANTHROPIC_MODEL`, `GOOGLE_MODEL`, `OPENAI_MODEL`) override `DEFAULT_MODELS` on Streamlit Cloud for cost control
- **New directories** (`pages/`, `components/`, `themes/`) are pure Python/CSS — no deployment changes needed

---

## 11. Out of Scope (Future)

These are explicitly **not** part of this spec but are noted for future reference:

- Per-page (local) parameters — to be specced when the first module needs them
- Strategy → Creative handoff (automated copy of creative brief between pages)
- Multiple workflows in the Workflow tab (second tab content)
- Tools module implementation beyond the holding message
- Page-specific descriptions (moved from sidebar — content TBD per page)
- Additional accent colours beyond `--accent-aquagreen` and `--accent-coral`

---

## 12. Implementation Order

Revised sequence — extract theme first, build the navigation shell, then add pages one at a time. Components are extracted alongside the pages that need them rather than all at once upfront.

1. **Extract theme CSS** → `frontend/themes/b3ta.css` (move CSS from `app.py`, update colour palette, add secondary colour vars)
2. **Create `app.py` navigation shell** → `sys.path` hack, `st.set_page_config`, theme loading, `st.navigation()` with placeholder page list, sidebar rendering
3. **Backend updates (core)** → `state.py` (optional `client_brief`, updated defaults), `provider.py` (add `model` parameter to `get_llm()`). These must land before Steps 4–5 because the strategy page needs `get_llm(provider=..., model=...)` and the creative page needs `client_brief` to be optional.
4. **Create `pages/workflow.py`** → move current pipeline logic from `app.py`, add tab scaffold, extract components as needed (`progress.py`, `history.py`, `run_metadata.py`, `agent_output.py`, `footer.py`)
5. **Create `pages/strategy.py`** → standalone strategist page, reuses `agent_output.py` and `footer.py`
6. **Create `pages/creative.py`** → standalone creative page, reuses `agent_output.py` and `footer.py`
7. **Create placeholder pages + Tools** → `marketing.py`, `production.py`, `agnostic.py` (hidden), `tools.py` (visible with `--accent-aquagreen` theme)
8. **Backend updates (config)** → `config.py` (per-provider model secrets, updated defaults for `MAX_ITERATIONS` and `APPROVAL_THRESHOLD`). Split from Step 3 because this doesn't block page creation — it only affects which model the sidebar defaults to.
9. **Verify `sys.path` resolution** → confirm that page files (`pages/strategy.py` etc.) can resolve `agt_sea` imports via the `sys.path` hack in `app.py`. Since `app.py` runs first and pages are loaded via `st.Page()` within the same process, this should work — but explicitly test it.
10. **Test end-to-end** → verify all four visible pages work (Strategy, Creative, Workflow, Tools), hidden placeholders don't appear, Streamlit Cloud deploys correctly
11. **Update `CLAUDE.md` and `README.md`** → reflect new project structure, commands, and current status

**Important:** Pause after each step for review before proceeding to the next.
