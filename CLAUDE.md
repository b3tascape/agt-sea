# agt_sea — AI Creative Agency Framework

Three AI agents (Strategist, Creative, Creative Director) collaborate via LangGraph to transform a client brief into a creative campaign concept. Provider-switchable (Anthropic/Google/OpenAI). Deployed on Streamlit Cloud.

See @README.md for full project overview and architecture diagram.

## Commands

```bash
uv sync                                    # Install dependencies
uv pip install -e .                        # Make agt_sea importable
uv run streamlit run frontend/app.py       # Run frontend locally
uv run python tests/test_pipeline.py       # Full pipeline test (real LLM calls)
uv run python -i tests/test_pipeline.py    # Interactive — explore final_state after run
uv run python tests/test_strategist.py     # Strategist only
uv run python tests/test_creative.py       # Strategist + Creative
uv run ruff check .                        # Lint
```

## Tech Stack

- Python 3.11+, managed with uv
- LangGraph for orchestration, LangChain for LLM abstraction
- Pydantic for data models and structured output (`with_structured_output()`)
- Streamlit for frontend, deployed to Streamlit Cloud
- Default LLM: Anthropic (claude-sonnet-4-6), switchable via `LLM_PROVIDER` env var or sidebar selector

## Project Structure

```
src/agt_sea/
├── config.py                # Settings, _get_secret() helper, st.secrets bridge, DEFAULT_MODELS + AVAILABLE_MODELS
├── agents/                  # One file per agent (strategist, creative, creative_director)
├── graph/workflow.py        # LangGraph graph definition, routing, finalisation nodes
├── llm/provider.py          # Provider-agnostic LLM factory (get_llm())
├── models/state.py          # Pydantic models (AgencyState, CDEvaluation, AgentOutput) and enums
└── prompts/
    ├── loader.py            # load_prompt() + load_creative_philosophy / load_strategic_philosophy / load_template / load_guidance wrappers
    ├── templates/           # Reusable structural scaffolds (e.g. creative_brief.txt)
    ├── guidance/            # Technique-specific guidance injected into agent prompts
    └── philosophies/
        ├── creative/        # One .txt file per CreativePhilosophy enum value
        └── strategic/       # One .txt file per StrategicPhilosophy enum value
frontend/
├── app.py                   # Navigation shell (sys.path hack, page config, theme, sidebar, routing)
├── pages/                   # One file per module (strategy, creative, workflow, tools + placeholders)
├── components/
│   ├── sidebar.py           # Logo, global params, footer
│   ├── agent_output.py      # Single agent output display
│   ├── history.py           # Pipeline history expanders
│   ├── run_metadata.py      # Run metrics bar
│   ├── progress.py          # Live node progress
│   ├── footer.py            # Footer badge
│   └── labels.py            # Shared enum → display-label mappings
└── themes/b3ta.css          # Theme CSS (single file, loaded once by app.py)
tests/
├── _helpers.py              # Shared utilities for manual integration tests
├── test_strategist.py       # Strategist isolation test
├── test_creative.py         # Strategist → Creative test
└── test_pipeline.py         # Full pipeline integration test
briefs/                      # Sample client briefs
docs/
├── architecture.md          # Mermaid workflow diagram
└── adr/                     # Architecture Decision Records (see @docs/adr/README.md)
```

## Code Style

- `from __future__ import annotations` at top of all modules
- Type hints on all function signatures and return types
- Docstrings on all modules and functions
- One function, one job

## Architecture Rules — IMPORTANT

- All agents import LLM via `from agt_sea.llm.provider import get_llm` — never instantiate models directly
- State flows through `AgencyState` (Pydantic) — agents read what they need, update fields, append to `history`
- Routing functions are pure: return strings only, NEVER mutate state
- State changes before END happen in dedicated finalisation nodes, not routing functions
- **Pass-through nodes are allowed** where a conditional edge needs a source node but no state mutation is required (e.g. `check_iterations` in `graph/workflow.py` is `lambda state: state`). The decision itself lives in the routing function attached to the node's conditional edges — this keeps routing pure while giving LangGraph the node it needs to branch from.
- **LangGraph boundary — Pydantic in, Pydantic out (rehydrate at the edge).** `AgencyState` is passed *into* `graph.invoke()` / `graph.stream()` as a Pydantic model. LangGraph returns a plain dict (and `stream()` yields per-node dict updates), so every call site that consumes graph output must rehydrate with `AgencyState.model_validate(raw)` before using it. Downstream code then uses attribute access (`state.status`, `state.history[0].evaluation.score`) — never `.get()` or `state["field"]`. For `stream()`, accumulate the per-node updates into a running dict first (`accumulated.update(node_output)`) and rehydrate once at the end — do not assume the last event contains the full state. See `frontend/pages/workflow.py` and `tests/test_pipeline.py` for the canonical pattern. Inside agent functions (which run *before* the boundary) attribute access already works.
- `config.py` uses `_get_secret()` which checks os.environ first, then st.secrets (for Streamlit Cloud)
- API keys are bridged from st.secrets -> os.environ at module load so LangChain providers can find them
- `get_llm()` accepts optional `provider` and `model` parameters for frontend sidebar overrides
- Selectable model lists for the sidebar live in `config.AVAILABLE_MODELS` (one list per provider). The sidebar imports from there — do not redefine model lists in `frontend/components/sidebar.py`. Any provider's `DEFAULT_MODELS` entry must appear in its `AVAILABLE_MODELS` list or the sidebar default falls back to index 0.
- Three philosophy fields live on `AgencyState`: `strategic_philosophy` (used by the Strategist), `creative_philosophy` (used by the Creative agent), and `cd_philosophy` (used by the Creative Director). All three default to `NEUTRAL`. The sidebar writes these to `st.session_state.strategic_philosophy`, `st.session_state.creative_philosophy`, and `st.session_state.cd_philosophy`; every page that builds an `AgencyState` must pass all three through.

## Agent Conventions

- Each agent function signature: `def run_agent(state: AgencyState) -> AgencyState`
- Each agent must: call `get_llm()`, update relevant state fields, append `AgentOutput` to `state.history`
- Each agent resolves provider/model as: `state.llm_provider or get_llm_provider()` and `state.llm_model or get_model_name(provider)` — this is how sidebar overrides reach the agents via `AgencyState.llm_provider` / `AgencyState.llm_model`
- `AgentOutput` must include: `agent`, `provider`, `model` (via `get_model_name()`), `iteration`, `content`, `timestamp`
- Creative Director uses `llm.with_structured_output(CDEvaluation)` for validated scoring
- Creative agent checks `state.cd_evaluation is not None` to determine initial vs revision path
- **Philosophy injection pattern** — Strategist, Creative, and Creative Director each build their system prompt via a module-level `_build_system_prompt(philosophy)` helper (Creative also has `_build_revision_prompt`). Each helper follows the *neutral-skip* rule: when the philosophy is `NEUTRAL`, `philosophy_section` stays empty and the prompt reads as if the feature wasn't there at all; otherwise the text is loaded via the appropriate `load_creative_philosophy` / `load_strategic_philosophy` wrapper and injected into a dedicated section. Strategist and Creative read `state.strategic_philosophy` / `state.creative_philosophy` respectively; the Creative Director reads `state.cd_philosophy` (not `state.creative_philosophy`).
- Strategist prompts are assembled from reusable pieces via `load_template()` (structural scaffold) and `load_guidance()` (technique-specific guidance) — don't hardcode the brief template or proposition guidance inline.

## Workflow Rules

- Run tests after making changes to agents or graph logic
- Run `ruff check .` before committing
- Commit messages: imperative mood, conventional commits (`feat:`, `fix:`, `chore:`, `docs:`)
- ADRs are append-only — new decisions get new numbered files, never edit old ones. The one exception is updating the `Status:` line of an older ADR to flag that it has been superseded (see ADR 0006 → 0007).
- When adding a new agent, follow the pattern in `agents/strategist.py`
- Explain your reasoning before making changes — what you're doing, why, and what alternatives you considered
- When introducing a new pattern or concept, explain it as if teaching a mid-level developer

## Deployment

- Streamlit Cloud auto-deploys from main branch
- `frontend/app.py` has `sys.path.insert` at top to resolve `agt_sea` imports on Streamlit Cloud
- Page files loaded via `st.Page()` run in the same process, so `sys.path` is already set when they execute
- API keys and config overrides go in Streamlit Cloud secrets dashboard, not .env
- Per-provider model secrets (`ANTHROPIC_MODEL`, `GOOGLE_MODEL`, `OPENAI_MODEL`) override defaults on Cloud for cost control

## Current Phase & Roadmap

**Current:** MODULE 01) Phase 6 — Refinement (error handling, frontend refinement, human-in-the-loop, logging/tracing)

**Multipage restructure complete** — frontend is a multipage Streamlit app with `st.navigation()`. Shared components live in `frontend/components/`, pages in `frontend/pages/`, theme in `frontend/themes/b3ta.css`.

**Modules planned:**
1. Workflows - Creative Campaign Development (Strategist -> Creative -> CD loop) — COMPLETE, deployed
2. Strategy - Standalone strategist page — COMPLETE (standalone, calls `run_strategist()` directly)
3. Creative - Standalone creative page — COMPLETE (standalone, calls `run_creative()` directly)
4. Tools - a suite of creative tools (Tools page visible with holding message)
5. Marketing - Standalone marketing agent(s) (placeholder page exists, not visible)
6. Production - Production services (e.g. Image, Audio, Film, Social content generation) (placeholder page exists, not visible)
7. Agnostic - Miscellaneous (placeholder page exists, not visible)

## Ignore these directories
- `.archive/` — contains snapshots, backups, and completed one-off specs, not working code. Never read from or execute anything in this directory.