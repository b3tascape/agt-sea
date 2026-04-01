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
├── config.py                # Settings, _get_secret() helper, st.secrets bridge
├── agents/                  # One file per agent (strategist, creative, creative_director)
├── graph/workflow.py        # LangGraph graph definition, routing, finalisation nodes
├── llm/provider.py          # Provider-agnostic LLM factory (get_llm())
├── models/state.py          # Pydantic models (AgencyState, CDEvaluation, AgentOutput) and enums
└── prompts/
    ├── loader.py            # load_philosophy_prompt() — reads prompt text from disk
    └── philosophies/        # One .txt file per CreativePhilosophy enum value
frontend/
├── app.py                   # Navigation shell (sys.path hack, page config, theme, sidebar, routing)
├── pages/                   # One file per module (strategy, creative, workflow, tools + placeholders)
├── components/              # Reusable UI components (sidebar, agent_output, history, progress, etc.)
└── themes/b3ta.css          # Theme CSS (single file, loaded once by app.py)
tests/                       # Integration tests — make real LLM calls, no mocks
briefs/                      # Sample client briefs
docs/adr/                    # Architecture Decision Records (see @docs/adr/index.md)
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
- `config.py` uses `_get_secret()` which checks os.environ first, then st.secrets (for Streamlit Cloud)
- API keys are bridged from st.secrets -> os.environ at module load so LangChain providers can find them
- `get_llm()` accepts optional `provider` and `model` parameters for frontend sidebar overrides

## Agent Conventions

- Each agent function signature: `def run_agent(state: AgencyState) -> AgencyState`
- Each agent must: call `get_llm()`, update relevant state fields, append `AgentOutput` to `state.history`
- `AgentOutput` must include: `agent`, `provider`, `model` (via `get_model_name()`), `iteration`, `content`, `timestamp`
- Creative Director uses `llm.with_structured_output(CDEvaluation)` for validated scoring
- Creative agent checks `state.cd_evaluation is not None` to determine initial vs revision path

## Workflow Rules

- Run tests after making changes to agents or graph logic
- Run `ruff check .` before committing
- Commit messages: imperative mood, conventional commits (`feat:`, `fix:`, `chore:`, `docs:`)
- ADRs are append-only — new decisions get new numbered files, never edit old ones
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

**Current:** MODULE 01) Phase 6 — Refinement (error handling, human-in-the-loop, logging/tracing)

**Multipage restructure complete** — frontend is now a multipage Streamlit app with `st.navigation()`. See `docs/SPEC-multipage.md` for the full spec.

**Modules planned:**
1. Workflows - Creative Campaign Development (Strategist -> Creative -> CD loop) — COMPLETE, deployed
2. Strategy - Standalone strategist page — COMPLETE (standalone, calls `run_strategist()` directly)
3. Creative - Standalone creative page — COMPLETE (standalone, calls `run_creative()` directly)
4. Tools - a suite of creative tools (Tools page visible with holding message)
5. Marketing - Standalone marketing agent(s) (placeholder page exists, not visible)
6. Production - Production services (e.g. Image, Audio, Film, Social content generation) (placeholder page exists, not visible)
7. Agnostic - Miscellaneous (placeholder page exists, not visible)