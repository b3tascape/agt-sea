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
- Default LLM: Anthropic (claude-sonnet-4-6), switchable via `LLM_PROVIDER` env var

## Project Structure

```
src/agt_sea/
├── config.py                # Settings, _get_secret() helper, st.secrets bridge
├── agents/                  # One file per agent (strategist, creative, creative_director)
├── graph/workflow.py        # LangGraph graph definition, routing, finalisation nodes
├── llm/provider.py          # Provider-agnostic LLM factory (get_llm())
└── models/state.py          # Pydantic models (AgencyState, CDEvaluation, AgentOutput) and enums
frontend/app.py              # Streamlit app (sys.path hack for Streamlit Cloud at top)
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
- API keys are bridged from st.secrets → os.environ at module load so LangChain providers can find them

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

## Deployment

- Streamlit Cloud auto-deploys from main branch
- `frontend/app.py` has `sys.path.insert` at top to resolve `agt_sea` imports on Streamlit Cloud
- API keys and config overrides go in Streamlit Cloud secrets dashboard, not .env
- Production uses `MODEL_NAME = claude-haiku-4-5-20251001` via Streamlit secret for cost control

## Current Phase & Roadmap

**Current:** Phase 6 — Refinement (error handling, human-in-the-loop, logging/tracing)

**Modules planned:**
1. Creative Campaign (Strategist → Creative → CD loop) ← COMPLETE, deployed
2. Brand Strategy (brand positioning, architecture)
3. Standalone Strategic Agents (e.g. creative brief writer)
4. Standalone Specialist Creative Agents (copywriter, art director, social creative)
