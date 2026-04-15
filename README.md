# 🌊 agt_sea

An AI-powered creative marketing tool for brands and agencies offering a number of services designed to improve creative output. 

The app is structured as a multipage Streamlit application with standalone modules for Strategy, Creative, and a full Workflow pipeline, plus a Tools page in development.

A Strategist writes the creative brief, a Creative generates ideas, and a Creative Director evaluates the work through a configurable creative philosophy. The system iterates until the work meets the quality threshold or the iteration budget is exhausted.

Built with LangGraph, LangChain, and Streamlit.

🔗 **[Live Demo](https://agt-sea.streamlit.app)**

---

## How It Works

```mermaid
graph LR
    A(["`**input:**
    Client brief supplied`"]):::input --> B["`**strategist**
    Creative brief written`"]:::agent

    B --> C["`**creative**
    Idea generation`"]:::agent

    C --> D["`**creative director**
    Evaluation:
    1. Rate creative
    2. Feedback`"]:::agent

    CP(["`**creative_philosophy**`"]):::philosophy --> D

    D --> E{"`**creative
    standard hit?**
    cd_score >= 80%`"}:::decision

    E -->|yes| G(["`**output:**
    Approved creative
    direction`"]):::output

    E -->|no| F{"`**max iterations
    reached?**
    iteration >= 3`"}:::decision

    F -->|no| C
    F -->|"`yes: output
    top scoring idea`"| G

    classDef input fill:#d3d3d3,color:#000,stroke:#999
    classDef agent fill:#2196F3,color:#fff,stroke:#1976D2
    classDef decision fill:#F5C542,color:#000,stroke:#D4A017
    classDef output fill:#d3d3d3,color:#000,stroke:#999
    classDef philosophy fill:#80deea,color:#000,stroke:#4dd0e1
```

The graph is defined in `graph/workflow.py` using LangGraph's `StateGraph`. Two conditional edges implement the approval gate and iteration limit. Routing functions are pure (return strings only). State mutations happen in dedicated finalisation nodes before `END`.

### Agents

| Agent | File | Role | Output |
|-------|------|------|--------|
| **Strategist** | `agents/strategist.py` | Transforms the raw client brief into a focused creative brief | Challenge, audience, insight, proposition, tone |
| **Creative** | `agents/creative.py` | Generates three distinct creative approaches per iteration | Concept title, core idea, execution, rationale |
| **Creative Director** | `agents/creative_director.py`| Evaluates creative work through a chosen philosophical lens | Structured score (0–100), strengths, weaknesses, direction |

The Creative agent has two prompt paths: initial generation (from brief only) and revision (incorporating CD feedback). It only sees the latest concept and latest feedback per iteration — not full history.

The Creative Director uses `with_structured_output(CDEvaluation)` to constrain LLM output to a validated Pydantic model.

All three agents build their system prompt via a module-level `_build_system_prompt(philosophy)` helper. When the philosophy is `NEUTRAL`, no philosophy section is injected and the prompt reads as if the feature wasn't there at all; otherwise the text is loaded from disk and injected into a dedicated section. The Strategist additionally assembles its prompt from a reusable creative-brief template and proposition guidance via `load_template()` / `load_guidance()`.


### Philosophies

Each agent runs through a configurable philosophical lens, set independently in the sidebar and stored on `AgencyState` as `strategic_philosophy`, `creative_philosophy`, and `cd_philosophy`. All three default to `neutral` (no lens injected).

**Creative philosophies** (shared by the Creative agent and Creative Director):

| Philosophy | Lens |
|-----------|------|
| Bold & Disruptive | Champions risk-taking and convention-breaking |
| Minimal & Refined | Values restraint, elegance, and precision |
| Emotionally Driven | Prioritises genuine human emotion and authenticity |
| Data Led | Demands strategic rationale grounded in evidence |
| Culturally Provocative | Champions cultural participation and relevance |

**Strategic philosophies** (used by the Strategist):

| Philosophy | Lens |
|-----------|------|
| Challenger | Positions the brand against a dominant incumbent or category orthodoxy |
| Human First | Leads from real human behaviour, needs, and tensions |
| Cultural Strategy | Reads cultural currents and gives the brand a role in them |
| Brand World | Builds a coherent brand universe with distinctive codes |
| Commercial Pragmatist | Prioritises clarity, commercial outcomes, and execution realism |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) |
| LLM Abstraction | [LangChain](https://github.com/langchain-ai/langchain) |
| Data Models | [Pydantic](https://docs.pydantic.dev/) |
| Frontend | [Streamlit](https://streamlit.io/) |
| Deployment | [Streamlit Cloud](https://streamlit.io/cloud) |
| Package Management | [uv](https://github.com/astral-sh/uv) |

### LLM Provider Support

The framework supports provider switching via configuration — change the `LLM_PROVIDER` environment variable to swap between:

- **Anthropic** (Claude) — default
- **Google** (Gemini)
- **OpenAI** (GPT)

---

## Data Model

Core state object: `AgencyState` (Pydantic `BaseModel` in `models/state.py`). This is the single source of truth passed through every graph node.

**Enums**: `WorkflowStatus`, `AgentRole`, `LLMProvider`, `CreativePhilosophy`, `StrategicPhilosophy` — all `str, Enum` for type safety and serialisation. Both philosophy enums include a `NEUTRAL` value that bypasses philosophy injection entirely.

**Supporting models**:
- `CDEvaluation` — structured evaluation (score 0–100 with validation, strengths, weaknesses, direction)
- `AgentOutput` — single agent output with metadata (agent, provider, model, iteration, content, timestamp, optional evaluation)

**State design**: Dual access pattern — latest outputs at top level (`creative_brief`, `creative_concept`, `cd_evaluation`) for quick access by downstream agents, plus a full ordered `history: list[AgentOutput]` for traceability and UI display.

**Graph boundary**: LangGraph accepts `AgencyState` on the way in but returns a plain dict on the way out (and `stream()` yields per-node dict updates). Call sites that consume graph output — the Workflow page and the pipeline test — rehydrate with `AgencyState.model_validate(raw)` at the boundary so downstream code uses attribute access and typed nested models (`AgentOutput`, `CDEvaluation`). For streaming, per-node updates are merged into a running dict first and rehydrated once at the end.

**Key fields on AgencyState**:
- `client_brief` — the raw brief supplied by the user
- `strategic_philosophy` (default `neutral`) — shapes the Strategist's lens when writing the creative brief
- `creative_philosophy` (default `neutral`) — shapes the Creative agent's lens when generating ideas
- `cd_philosophy` (default `neutral`) — shapes the Creative Director's evaluation lens
- `llm_provider` (optional override) — when set, agents use this provider instead of the config default. Populated from the sidebar selector on each run.
- `llm_model` (optional override) — when set, agents use this model name instead of `get_model_name(provider)`. Populated from the sidebar selector on each run.
- `approval_threshold` (default `80.0`) — minimum CD score required for approval
- `max_iterations` (default `3`) — hard cap on creative loop iterations
- `iteration` — incremented by the Creative agent on each pass
- `status` — tracks workflow lifecycle via `WorkflowStatus` enum

Thresholds and max iterations are set per [ADR 0007](docs/adr/0007-revised-loop-thresholds.md), which supersedes the original values from [ADR 0006](docs/adr/0006-iterative-loop-design.md).

---

## Configuration

Application settings are centralised in `config.py` and accessed via helper functions. The `_get_secret()` helper reads from environment variables first, falling back to Streamlit secrets for cloud deployment.

A bridge at module load injects API keys from `st.secrets` into `os.environ` so LangChain providers (which read keys directly from the environment) work on Streamlit Cloud without modification.

Settings include: LLM provider, model name per provider, max iterations, approval threshold, transport retry count, and the public-demo run cap. All overridable via environment variables or Streamlit secrets:

- `LLM_PROVIDER`, `ANTHROPIC_MODEL`, `GOOGLE_MODEL`, `OPENAI_MODEL` — provider and per-provider model overrides
- `MAX_ITERATIONS` (default `3`) — hard cap on creative loop iterations
- `APPROVAL_THRESHOLD` (default `80.0`) — minimum CD score required for approval
- `LLM_MAX_RETRIES` (default `3`) — attempts made by `wrap_with_transport_retry()` on transient transport errors (see ADR 0012)
- `DEMO_RUN_CAP` (default `10`) — per-session run limit for the public demo (see ADR 0013)

**Default models** (local/development tier), defined in `config.DEFAULT_MODELS`:
- Anthropic: `claude-sonnet-4-6`
- Google: `gemini-3-flash-preview`
- OpenAI: `gpt-5.4-mini`

The set of models selectable in the sidebar lives in `config.AVAILABLE_MODELS` (one list per provider) — the sidebar imports this dict directly, so config is the single source of truth for both the default and the selectable options.

**Deployment note**: Streamlit Cloud uses per-provider model secrets (e.g. `ANTHROPIC_MODEL=claude-haiku-4-5-20251001`) set in the secrets dashboard for cost control. The sidebar model selector defaults to whatever the config resolves for the active provider.

---


## Project Structure

```
agt_sea/
├── docs/
│   ├── architecture.md              # Mermaid graph diagram
│   └── adr/                         # Architecture Decision Records
├── src/
│   └── agt_sea/
│       ├── config.py                # Settings, env vars, st.secrets bridge
│       ├── agents/
│       │   ├── strategist.py        # Brief -> creative brief
│       │   ├── creative.py          # Creative brief -> concepts
│       │   └── creative_director.py # Concepts -> evaluation
│       ├── graph/
│       │   └── workflow.py          # LangGraph orchestration
│       ├── llm/
│       │   └── provider.py          # LLM provider abstraction
│       ├── models/
│       │   └── state.py             # Pydantic data models & enums
│       ├── prompts/
│       │   ├── loader.py            # load_prompt() + load_creative_philosophy / load_strategic_philosophy / load_template / load_guidance
│       │   ├── templates/           # Reusable structural scaffolds (e.g. creative_brief.txt)
│       │   ├── guidance/            # Technique-specific guidance injected into agent prompts
│       │   └── philosophies/
│       │       ├── creative/        # One .txt file per CreativePhilosophy enum value
│       │       └── strategic/       # One .txt file per StrategicPhilosophy enum value
├── tests/
│   ├── _helpers.py                      # Shared test utilities (load_brief, print_entry_fields)
│   ├── test_strategist.py               # Strategist isolation test (manual, real LLM)
│   ├── test_creative.py                 # Strategist -> Creative test (manual, real LLM)
│   ├── test_pipeline.py                 # Full pipeline integration test (manual, real LLM)
│   ├── test_pipeline_failure.py         # Pipeline failure-path pytest unit tests
│   ├── test_creative_director_retry.py  # CD validation-retry helper pytest unit tests
│   ├── test_llm_provider.py             # get_llm() / retry-wrapper pytest unit tests
│   └── test_run_guard.py                # Run guard counter pytest unit tests
├── frontend/
│   ├── app.py                       # Navigation shell (entry point, session state defaults)
│   ├── pages/
│   │   ├── strategy.py              # Standalone strategist
│   │   ├── creative.py              # Standalone creative
│   │   ├── workflow.py              # Full pipeline (tabbed)
│   │   ├── tools.py                 # Tools (holding message)
│   │   ├── marketing.py             # Placeholder (hidden)
│   │   ├── production.py            # Placeholder (hidden)
│   │   └── agnostic.py              # Placeholder (hidden)
│   ├── components/
│   │   ├── sidebar.py               # Logo, global params, footer
│   │   ├── agent_output.py          # Single agent output display
│   │   ├── history.py               # Pipeline history expanders
│   │   ├── run_metadata.py          # Run metrics bar
│   │   ├── progress.py              # Live node progress
│   │   ├── footer.py                # Footer badge
│   │   ├── error_state.py           # Failure UI (renders state.error on FAILED runs)
│   │   ├── run_guard.py             # Per-session run counter gate (ADR 0013)
│   │   └── labels.py                # Shared enum → display-label mappings
│   └── themes/
│       └── b3ta.css                 # Theme CSS
├── .streamlit/
│   └── config.toml                  # Streamlit config (pins light theme)
├── briefs/
│   └── sample_brief_001.txt         # Sample client brief
├── pyproject.toml
├── .env.example
├── CLAUDE.md
├── LICENSE
└── README.md
```

## Coding Conventions

- All agents import LLM via `from agt_sea.llm.provider import get_llm` — never instantiate models directly
- State flows through `AgencyState` — agents read what they need and append to history
- Routing functions are pure (return strings, no state mutation) — state changes happen in dedicated nodes
- Type hints on all function signatures
- Every module and function should have a docstring
- `from __future__ import annotations` at the top of every file
- Enums for fixed vocabularies (providers, roles, statuses, philosophies) — never raw strings
- Config-driven where possible — defaults in code, environment overrides them
- Conventional commits style for commit messages (imperative mood)
- ADRs are append-only — new decisions get new numbered files; older ADRs are superseded rather than edited, with only the `Status:` line updated to flag the supersession
- All new files should follow existing patterns in the codebase

## File Conventions

- API keys: `.env` in project root (gitignored)
- Philosophy prompts: plain text files in `prompts/philosophies/creative/` and `prompts/philosophies/strategic/`, loaded by the convenience wrappers in `prompts/loader.py` (future: RAG-enhanced)
- Prompt templates & guidance: plain text files in `prompts/templates/` and `prompts/guidance/`, loaded by `load_template()` / `load_guidance()` and composed inside agent `_build_system_prompt()` helpers
- Agent system prompts: assembled inline in agent files via `_build_system_prompt()` helpers that compose templates, guidance, and philosophy text
- Sample briefs: `briefs/` directory
- Architecture docs: `docs/architecture.md` (Mermaid)
- Decision records: `docs/adr/` (numbered markdown files + README index)

## Key Design Principles

- Modular architecture — each module is independently developable
- Provider-agnostic AI — switching between Anthropic, Google, OpenAI requires only a config/env change
- Iterative refinement — creative work improves through structured feedback loops with bounded execution
- Separation of routing and state — routing functions decide flow, nodes modify state
- Build incrementally — each phase produces something runnable
- Config over hardcoding — API keys, model names, thresholds, prompts all configurable
- Understand before extending — every file should be readable and explainable
- Clean, readable Python with clear separation of concerns
- Professional, portfolio-grade code and documentation

---

## Architecture Decisions

Key technical decisions are documented as Architecture Decision Records in [`docs/adr/`](docs/adr/):

- **ADR 0001** — LangGraph for orchestration
- **ADR 0002** — LangChain for LLM provider switching
- **ADR 0003** — Pydantic for state and data modelling *(boundary handling refined by ADR 0011)*
- **ADR 0004** — Structured output for CD evaluation
- **ADR 0005** — Streamlit for frontend
- **ADR 0006** — Iterative creative loop with bounded execution *(thresholds superseded by ADR 0007)*
- **ADR 0007** — Revised creative loop thresholds (80 / 3)
- **ADR 0008** — Multipage frontend architecture
- **ADR 0009** — LLM provider and model override mechanism
- **ADR 0010** — Filesystem-backed prompt injection pattern
- **ADR 0011** — Rehydrate LangGraph output to Pydantic at the boundary
- **ADR 0012** — Error handling and graceful degradation (two-layer retry, `FAILED` contract, `_safe_node` wrapper)
- **ADR 0013** — Demo abuse mitigation via per-session run counter

## Build Sequence

1. **MVP — Creative Pipeline** ← COMPLETE (deployed to Streamlit Cloud)
2. **Standalone Strategic Agents (e.g. creative brief writer**)** ← COMPLETE (standalone, calls `run_strategist()` directly)
3. **Standalone Creative Agents (discipline-specific specialists, different creative types)** ← COMPLETE (standalone, calls `run_creative()` directly)
4. **Error handling & graceful degradation (retries, failure contract)** ← COMPLETE (Phase 6.1 / ADRs 0012 & 0013)
5. RAG-enhanced creative philosophies
6. Human-in-the-loop approval points
7. Structured logging & tracing (LangSmith)
8. Brand Strategy Module (branding / brand positioning)
9. Provider comparison tooling

---

## Status

🟢 **Multipage app deployed** — multipage Streamlit frontend with standalone Strategy, Creative, and Workflow modules. Deployed to Streamlit Cloud with auto-deploy on push.

### Roadmap

**Phase 6 — Refinement (current)**
- [ ] Frontend refinement and UX polish
- [x] Error handling and graceful degradation
- [ ] Human-in-the-loop approval points (LangGraph interrupt/resume)
- [ ] Structured logging and tracing (LangSmith)

**Future Modules**
- [ ] Tools - a suite of creative tools (page visible with holding message)
- [ ] Marketing - Standalone marketing agent(s) (placeholder page exists)
- [ ] Production - Production services (e.g. Image, Audio, Film, Social content generation) (placeholder page exists)
- [ ] Agnostic - Miscellaneous (placeholder page exists)
---

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- An API key for at least one supported LLM provider

### Installation

```bash
# Clone the repo
git clone https://github.com/b3tascape/agt-sea.git
cd agt-sea

# Install dependencies
uv sync
uv pip install -e .

# Set up environment variables
cp .env.example .env
# Edit .env and add your API key(s)
```

### Run the Frontend locally

```bash
uv run streamlit run frontend/app.py
```

### Run full pipeline test (makes real LLM calls)

```bash
uv run python tests/test_pipeline.py
```

### Run individual agent tests

```bash
uv run python tests/test_strategist.py
uv run python tests/test_creative.py
```

### Interactive pipeline exploration

```bash
uv run python -i tests/test_pipeline.py
# Then: final_state["history"][0].agent, final_state["status"], etc.
```

---

## License

MIT — see [LICENSE](LICENSE) for details.