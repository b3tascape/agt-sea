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
uv run python tests/test_creative1.py      # Strategist + Creative 1 (Standard 2.0)
uv run python tests/test_creative2.py      # Strategist + Creative 1 + Creative 2 (Standard 2.0)
uv run python tests/test_pipeline_v2.py    # Full Standard 2.0 pipeline — pauses at interrupt, auto-selects territory[0]
uv run ruff check .                        # Lint
uv run pytest tests/                       # Unit tests (excludes manual integration scripts)
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
├── agents/                  # One file per agent (strategist, creative, creative_director, creative1, creative2, cd_grader, cd_feedback, cd_synthesis)
├── graph/
│   ├── workflow.py          # Standard 1.0 LangGraph graph (strategist → creative → CD loop)
│   └── workflow_v2.py       # [2.0] Standard 2.0 graph — multi-stage pipeline with territory-selection interrupt
├── llm/provider.py          # Provider-agnostic LLM factory (get_llm())
├── models/state.py          # Pydantic models (AgencyState, CDEvaluation, AgentOutput) and enums
└── prompts/
    ├── loader.py            # load_prompt() + load_creative_philosophy / load_strategic_philosophy / load_provenance / load_taste / load_template / load_guidance wrappers
    ├── templates/           # Reusable structural scaffolds (e.g. creative_brief.txt)
    ├── guidance/            # Technique-specific guidance injected into agent prompts
    ├── provenance/          # [2.0] One .txt file per non-NEUTRAL Provenance enum value
    ├── taste/               # [2.0] One .txt file per non-NEUTRAL Taste enum value
    └── philosophies/
        ├── creative/        # One .txt file per CreativePhilosophy enum value
        └── strategic/       # One .txt file per StrategicPhilosophy enum value
frontend/
├── app.py                   # Navigation shell (sys.path hack, page config, theme, session state defaults, sidebar, routing)
├── pages/                   # One file per module (strategy, creative, workflow, tools + placeholders)
├── components/
│   ├── sidebar.py           # Logo, global params, footer
│   ├── agent_output.py      # Single agent output display
│   ├── history.py           # Pipeline history expanders
│   ├── run_metadata.py      # Run metrics bar
│   ├── progress.py          # Live node progress
│   ├── footer.py            # Footer badge
│   ├── error_state.py       # Failure UI (renders state.error on FAILED runs)
│   ├── run_guard.py         # Per-session run counter gate (ADR 0013)
│   ├── territory_cards.py   # [2.0] Renders list[Territory] as modular bordered cards
│   └── labels.py            # Shared enum → display-label mappings
└── themes/b3ta.css          # Theme CSS (single file, loaded once by app.py)
tests/
├── _helpers.py                      # Shared utilities for manual integration tests
├── test_strategist.py               # Strategist isolation test (manual, real LLM)
├── test_creative.py                 # Strategist → Creative test (manual, real LLM)
├── test_creative1.py                # [2.0] Strategist → Creative 1 test (manual, real LLM)
├── test_creative2.py                # [2.0] Strategist → Creative 1 → Creative 2 test (manual, real LLM)
├── test_pipeline.py                 # Full pipeline integration test (manual, real LLM)
├── test_pipeline_v2.py              # [2.0] Full Standard 2.0 pipeline test — pauses at interrupt, resumes with territory[0] (manual, real LLM)
├── test_pipeline_failure.py         # Pipeline failure-path pytest unit tests
├── test_creative_director_retry.py  # Validation-retry helper pytest unit tests (via CDEvaluation)
├── test_cd_grader.py                # [2.0] GraderEvaluation schema + retry-helper bind pytest unit tests
├── test_cd_synthesis.py             # [2.0] CDSynthesis / ConceptScoreSummary schema pytest unit tests
├── test_llm_provider.py             # get_llm() / retry-wrapper pytest unit tests
└── test_run_guard.py                # Run guard counter pytest unit tests
.streamlit/config.toml       # Streamlit config — pins base theme to light
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
- `get_llm()` accepts optional `provider`, `model`, and `temperature` parameters for frontend sidebar overrides. `temperature` is `float | None` — when `None` (the default) the argument is omitted from the provider chat-model constructor and each provider's server-side default applies; when set it is passed through to `ChatAnthropic` / `ChatGoogleGenerativeAI` / `ChatOpenAI`. `temperature` is orthogonal to `with_retry` (temperature is fixed at construction, retry wrapping happens afterwards). Standard 1.0 agents (Strategist / Creative / CD) pass `temperature=0.7` explicitly to preserve their prior behaviour; Standard 2.0 agents read the appropriate per-agent temperature from `AgencyState`.
- Selectable model lists for the sidebar live in `config.AVAILABLE_MODELS` (one list per provider). The sidebar imports from there — do not redefine model lists in `frontend/components/sidebar.py`. Any provider's `DEFAULT_MODELS` entry must appear in its `AVAILABLE_MODELS` list or the sidebar default falls back to index 0.
- Three philosophy fields live on `AgencyState`: `strategic_philosophy` (used by the Strategist), `creative_philosophy` (used by the Creative agent), and `cd_philosophy` (used by the Creative Director). All three default to `NEUTRAL`. The sidebar writes these to `st.session_state.strategic_philosophy`, `st.session_state.creative_philosophy`, and `st.session_state.cd_philosophy`; every page that builds an `AgencyState` must pass all three through.
- **Standard 2.0 data model (ADR 0014)** — the multi-stage pipeline adds supporting models alongside `CDEvaluation` / `AgentOutput` in `models/state.py`: `Territory`, `CampaignDeliverable`, `CampaignConcept`, `GraderEvaluation`, `ConceptScoreSummary`, `CDSynthesis`. Two new prompt-injection enums alongside `CreativePhilosophy` / `StrategicPhilosophy`: `Provenance` (`NEUTRAL` + `NORTHERN_WORKING_CLASS`, `METROPOLITAN_ACADEMIC`, `DIY_SUBCULTURE`) and `Taste` (`NEUTRAL` + `UNDERGROUND_REFERENTIAL`, `AVANT_GARDE`, `POP_MAXIMALIST`, `CRAFT_TRADITIONALIST`). Prompt content for both lives as one `.txt` file per non-NEUTRAL enum value in `prompts/provenance/` and `prompts/taste/`, loaded via `load_provenance()` / `load_taste()` in `prompts/loader.py`. Same neutral-skip convention as the philosophy wrappers: callers check for NEUTRAL and skip the load. The v1 `creative_director.py` and v1 `workflow.py` are untouched; v2 agents and graph live in separate files.
- **Per-role prompt-injection lenses on `AgencyState`** — Standard 2.0 carries one provenance + one taste field *per creative role*: `creative1_provenance`/`creative1_taste`, `creative2_provenance`/`creative2_taste`, and `cd_provenance`/`cd_taste` shared by CD Feedback and CD Synthesis. All default to `NEUTRAL`. The CD Grader is always neutral by contract — never inject philosophy, provenance, or taste into it. Same sidebar-mirrors-state convention as the existing philosophy fields; the provenance/taste fields slot in alongside the philosophies in the `# --- Input ---` block, with a `# [2.0]` marker.
- **Per-agent temperature on `AgencyState`** — temperature lives per agent so values flow through the graph and are recorded for reproducibility: `creative1_temperature`, `creative2_temperature`, `cd_feedback_temperature`, `cd_synthesis_temperature` (all default `0.7`), and `grader_temperature` (default `0.0`, not sidebar-exposed — hardcoded for repeatable scoring). All are bounded `0.0–1.0` (Anthropic's cap). Agents pass the value through to `get_llm(temperature=...)`; the `temperature` parameter lands on `get_llm()` in Phase B. Fields slot into the `# --- Iteration tracking ---` block alongside `max_iterations` / `approval_threshold`.
- **Standard 2.0 agent-output fields on `AgencyState`** — `territories: list[Territory]` + `num_territories: int` (default 3, bounded 1–12) + `selected_territory: Territory | None` + `territory_rejection_context: str | None` for the territory stage; `campaign_concept: CampaignConcept | None`, `grader_evaluation: GraderEvaluation | None`, `cd_feedback_direction: str | None`, `cd_synthesis: CDSynthesis | None` for the campaign stage. All live in the existing `# --- Agent outputs ---` block with a `# [2.0]` marker — not segregated into a separate section. The interrupt node and checkpointer that operationalise these fields land in Phase D.
- **Structured output for list-valued schemas — wrapper model required.** LangChain's `with_structured_output()` rejects bare generic aliases like `list[Territory]` at composition time (`ValueError: callable list[...] is not supported by signature`). Agents that produce a list as their structured output must define a local wrapper model (e.g. `class TerritorySet(BaseModel): territories: list[Territory]` inside `agents/creative1.py`), pass the wrapper to `with_structured_output()`, and unwrap the list before writing to state. These wrappers are implementation details of the agent — keep them module-local, do not add them to `models/state.py`, and do not propagate the wrapper type beyond the agent boundary.
- **Agent input contract is agent-scoped, not caller-scoped.** When an agent reads an optional state field (e.g. `territory_rejection_context`), it reads it regardless of who is calling — graph, standalone page, test, future caller. Fields that are semantically inputs belong in the agent's read-set; do not scope reads to a specific caller.
- **State organisation — don't segregate by workflow version.** `AgencyState` is one object shared by both Standard 1.0 and Standard 2.0. When adding new fields, extend the existing functional groups (`Input`, `LLM overrides`, `Agent outputs`, `Iteration tracking`, `History`, `Workflow`) rather than trailing a "v2" section. A subtle `# [2.0] …` marker inside a group is fine to cluster related fields; a top-level version split is not.
- **Safe-node wrapper** — every agent node is wrapped with `_safe_node()` at graph-build time in `graph/workflow.py`. New agents inherit failure handling by construction — do not add `try`/`except` inside agent functions. The error-string format is owned by `format_node_error(fn_name, exc)` in the same module; standalone pages that call agents directly outside the graph (e.g. `frontend/pages/strategy.py`, `frontend/pages/creative.py`) must import and use it to construct `state.error` so the display contract stays consistent. See ADR 0012.
- **Failure contract** — `WorkflowStatus.FAILED` and `state.error` are the contract between the graph and the frontend. On failure, routing diverts to a `finalise_failed` node → `END`. Frontend pages check `state.status == WorkflowStatus.FAILED` after rehydration and render the `error_state` component instead of agent output. Routing functions begin with a uniform `if state.error is not None: return "failed"` guard — the mutation already happened in `_safe_node`.
- **Standard 2.0 graph (ADR 0014)** — `graph/workflow_v2.py` defines the multi-stage v2 pipeline: `strategist → creative1 → interrupt_territory_selection → creative2 → cd_grader → (cd_feedback loop | cd_synthesis) → finalise_*`. v1's `graph/workflow.py` is untouched. Both compile independently; the workflow page picks one per tab. The shared pieces with v1 are `format_node_error` (imported from v1) and the `_check_failed` routing pattern. **v2 has its own `_safe_node`** because v1's naive `except Exception` would swallow `GraphInterrupt` (which is an `Exception` subclass) and break the pause; the v2 wrapper re-raises `GraphBubbleUp` so LangGraph's control-flow signals propagate.
- **Checkpointer is a module-scope singleton.** `workflow_v2.py` instantiates `_CHECKPOINTER = MemorySaver()` at module import time and passes that same instance to every `StateGraph.compile(checkpointer=...)` call. This is deliberate: Streamlit re-runs the page script on every interaction, which means `build_graph_v2()` is called repeatedly. A per-call `MemorySaver()` would erase in-flight interrupts. A module-scope singleton survives within the Python process but does not survive a restart / redeploy — persistent checkpointing (SQLite/Postgres) is the upgrade path.
- **Interrupt node is idempotent.** LangGraph resumes an interrupted node by **re-executing it from the top** — everything above `interrupt()` runs again on every resume. `_interrupt_territory_selection` therefore only reads state and sets fields derived from the resume value (`selected_territory`, `territory_rejection_context`). No history appends, no counters, no LLM calls, no mutations before `interrupt()` (those aren't captured in the paused checkpoint anyway — LangGraph snapshots at the end of the *previous* node, not at the start of the interrupted one). Consequence: there is no `WorkflowStatus` value that mirrors "paused" — the authoritative pause signal is LangGraph's own (`graph.get_state(config).interrupts` / the `__interrupt__` event from `stream()`).
- **Thread config is mandatory on v2.** Every `agency_graph_v2.invoke(...)` / `.stream(...)` call must include `config={"configurable": {"thread_id": "<id>"}}`. The same `thread_id` links the initial run to the resume. Callers own the ID (Streamlit stores it in `st.session_state`, tests generate a fresh UUID per run).
- **Resuming a v2 run.** Pass `Command(resume=<value>)` — from `langgraph.types` — as the *input* to a subsequent `stream()` / `invoke()` call with the same thread config. The resume value is whatever `interrupt()` returns inside the node. The v2 interrupt node's contract accepts `{"action": "select", "index": int}` or `{"action": "rerun", "rejection_context": str | None}`. See `frontend/pages/workflow.py` (Phase E) and `tests/test_pipeline_v2.py` for the canonical pattern.
- **Boundary rehydration on v2 is identical to v1 — Pydantic in, dict out.** `graph.invoke(state, config=cfg)` and `graph.stream(state, config=cfg)` return plain dicts exactly like v1. After an interrupt, read the paused state via `graph.get_state(cfg).values` (also a plain dict) and rehydrate with `AgencyState.model_validate(values)` before attribute access. The interrupt pattern does **not** change this rule. `config` is required only on the LangGraph calls themselves — rehydration is unchanged.

## Agent Conventions

- Each agent function signature: `def run_agent(state: AgencyState) -> AgencyState`
- Each agent must: call `get_llm()`, update relevant state fields, append `AgentOutput` to `state.history`
- Each agent resolves provider/model as: `state.llm_provider or get_llm_provider()` and `state.llm_model or get_model_name(provider)` — this is how sidebar overrides reach the agents via `AgencyState.llm_provider` / `AgencyState.llm_model`
- `AgentOutput` must include: `agent`, `provider`, `model` (via `get_model_name()`), `iteration`, `content`, `timestamp`
- Creative Director uses `llm.with_structured_output(CDEvaluation)` for validated scoring
- Creative agent checks `state.cd_evaluation is not None` to determine initial vs revision path
- **Philosophy injection pattern** — Strategist, Creative, and Creative Director each build their system prompt via a module-level `_build_system_prompt(philosophy)` helper (Creative also has `_build_revision_prompt`). Each helper follows the *neutral-skip* rule: when the philosophy is `NEUTRAL`, `philosophy_section` stays empty and the prompt reads as if the feature wasn't there at all; otherwise the text is loaded via the appropriate `load_creative_philosophy` / `load_strategic_philosophy` wrapper and injected into a dedicated section. Strategist and Creative read `state.strategic_philosophy` / `state.creative_philosophy` respectively; the Creative Director reads `state.cd_philosophy` (not `state.creative_philosophy`).
- **Creative 1 (Standard 2.0) — `_build_system_prompt(philosophy, provenance, taste, num_territories)`.** Creative 1 composes three neutral-skip sections (philosophy, provenance, taste) and interpolates `num_territories` into the prompt body so the agent asks for exactly the count `AgencyState.num_territories` requests — never hardcode "three". Reads `state.creative_philosophy`, `state.creative1_provenance`, `state.creative1_taste`. Rejection context (`state.territory_rejection_context`) is steered in the human message rather than the system prompt (per-run context, not a persistent lens) and follows the same neutral-skip rule — when `None`, nothing is injected. Uses `AgentRole.CREATIVE_1` on its `AgentOutput`. The territory-count interpolation pattern generalises: any future agent whose output cardinality is user-configurable should interpolate the count into the prompt body rather than hardcoding it.
- **Creative 2 (Standard 2.0) — `_build_system_prompt(philosophy, provenance, taste)` + `_build_revision_prompt(philosophy, provenance, taste)`.** Two prompt paths like Standard 1.0's Creative: initial path when the revision inputs are absent, revision path when both `state.grader_evaluation` and `state.cd_feedback_direction` are populated. Reads `state.creative_philosophy`, `state.creative2_provenance`, `state.creative2_taste`, and `state.selected_territory` (required — raises `ValueError` when `None` before any LLM call). Produces a structured `CampaignConcept` via `with_structured_output()`; the response goes through `invoke_with_validation_retry` so schema validation failures get one reprompt before surfacing as a FAILED run. Uses `AgentRole.CREATIVE_2`.
- **CD Grader (Standard 2.0) — `_build_system_prompt()` (no parameters).** Lean by contract: no philosophy, provenance, or taste injection. The prompt is fixed and drafted in this phase (ADR 0014 marked it TBC). Design intent: unambiguous scoring bands, objectivity language, explicit "no coaching" instruction to keep the grader out of CD Feedback's lane. Temperature comes from `state.grader_temperature` (default `0.0` on state — kept on state rather than hardcoded so recorded run metadata matches the actual LLM call). Produces a structured `GraderEvaluation` (score + rationale only) via `with_structured_output()` + `invoke_with_validation_retry`. Uses `AgentRole.CD_GRADER`.
- **CD Feedback (Standard 2.0) — `_build_system_prompt(philosophy, provenance, taste)` + `_build_human_message(...)`.** Reads the CD injection lenses (`cd_philosophy`, `cd_provenance`, `cd_taste`) and requires `state.campaign_concept`. `state.grader_evaluation` is *optional* in the human message — when present the score and rationale are rendered, when `None` the grader block is omitted so the prompt doesn't fabricate a score. Produces **free-text** output via `llm.invoke(...).content`, written to `state.cd_feedback_direction`. No structured output, no validation retry — the direction is the product, and format constraints (prose vs bullets) are deliberately omitted in the prompt. The system prompt was drafted in this phase (ADR 0014 marked it TBC); design intent: no scoring, no assumption of graph context (loops/thresholds are the graph's concern), no imposed output format. Uses `AgentRole.CD_FEEDBACK`.
- **CD Synthesis (Standard 2.0) — `_build_system_prompt(philosophy, provenance, taste)`.** Reads the CD injection lenses (same `cd_*` fields as CD Feedback), `state.campaign_concept` (required), `state.grader_evaluation` (optional), and `state.history` (rendered as a compact one-line-per-entry log). Produces a structured `CDSynthesis` via `with_structured_output()` + `invoke_with_validation_retry`. Schema built to support N concepts for the future parallel variant — the system prompt explicitly instructs the LLM to leave `comparison_notes` as `None` when only one concept has been developed (the simplified v2 graph's case) and populate it when multiple have been. The system prompt was drafted in this phase (ADR 0014 marked it TBC); design intent: confident recommendation voice, this is the output the user sees, not a review. Uses `AgentRole.CD_SYNTHESIS`.
- **CD agents are campaign-scoped.** CD Grader, CD Feedback, and CD Synthesis all operate on `state.campaign_concept`. Territories are handled by the human at the interrupt — the CD agents do not evaluate or coach on territories.
- **Validation retry helper is shared.** `invoke_with_validation_retry` lives in `agt_sea/llm/provider.py` (not `agents/creative_director.py` where it first appeared). It is generic over any Pydantic model via `TypeVar("_StructuredT", bound=BaseModel)`. Agents that use `with_structured_output()` (Creative 1, Creative 2, Creative Director, CD Grader, CD Synthesis) should import and use it rather than invoking the structured runnable directly — this keeps the one-shot reprompt-on-ValidationError behaviour consistent across every schema-enforced agent.
- Strategist prompts are assembled from reusable pieces via `load_template()` (structural scaffold) and `load_guidance()` (technique-specific guidance) — don't hardcode the brief template or proposition guidance inline.
- **Logging** — agents use stdlib `logging` for runtime diagnostics. Module-level convention: `logger = logging.getLogger(__name__)` at the top of the file, `logger.warning()` for recoverable anomalies (e.g. retry paths), `logger.error()` for failures. Introduced in Phase 6.1 alongside the CD validation-retry helper; Phase 6.4 will layer structured logging/tracing on top.
- **Run guard** — every agent-invoking frontend page must call `check_run_allowed()` from `frontend/components/run_guard.py` before constructing `AgencyState` or calling an agent. If it returns `False`, render `render_run_limit_reached()` and `st.stop()`. The check-and-increment is atomic, so callers cannot forget to bump the counter. Cap is `config.DEMO_RUN_CAP` (default 10, env-overridable). See ADR 0013.

## Workflow Rules

- Run tests after making changes to agents or graph logic
- Run `ruff check .` before committing
- Commit messages: imperative mood, conventional commits (`feat:`, `fix:`, `chore:`, `docs:`)
- ADRs are append-only — new decisions get new numbered files, never edit old ones. The one exception is updating the `Status:` line of an older ADR to flag that it has been superseded or refined (see ADR 0006 → 0007, ADR 0003 → 0011).
- Workplans live at `docs/workplans/` while work is in progress. When a workplan's work is complete and its corresponding ADR is committed, move it to `.archive/workplans/` with `git mv`. Specs follow the same pattern: live specs in `docs/specs/`, completed specs in `.archive/specs/`. The permanent record of decisions lives in `docs/adr/` — workplans and specs are transient scaffolding, ADRs are the durable artefact.
- When adding a new agent, follow the pattern in `agents/strategist.py`
- Explain your reasoning before making changes — what you're doing, why, and what alternatives you considered
- When introducing a new pattern or concept, explain it as if teaching a mid-level developer

## Deployment

- Streamlit Cloud auto-deploys from main branch
- `frontend/app.py` has `sys.path.insert` at top to resolve `agt_sea` imports on Streamlit Cloud
- Page files loaded via `st.Page()` run in the same process, so `sys.path` is already set when they execute
- API keys and config overrides go in Streamlit Cloud secrets dashboard, not .env
- Per-provider model secrets (`ANTHROPIC_MODEL`, `GOOGLE_MODEL`, `OPENAI_MODEL`) override defaults on Cloud for cost control
- `.streamlit/config.toml` pins `base = "light"` so the app never falls through to Streamlit's dark theme regardless of user OS preference. All visual styling comes from `b3ta.css`.
- `app.py` initialises session state defaults (philosophies, provider, model, thresholds, `run_count`, and the Standard 2.0 per-role provenance / taste + per-agent temperature fields) via `setdefault` before the sidebar renders, so pages never hit a missing key even if the sidebar fails on first load
- **Sidebar scope** — top-level controls are shared by Standard 1.0 and 2.0 (philosophies, provider, model, max iterations, approval threshold). Standard 2.0-specific controls (per-role provenance + taste selectors for Creative 1 / Creative 2 / CD, and per-agent temperature sliders for Creative 1, Creative 2, CD Feedback, CD Synthesis) live inside a single collapsed `st.sidebar.expander("STANDARD 2.0 CONTROLS")` block. Streamlit does not allow nested expanders, so each role is a markdown sub-heading inside the single expander. CD Grader is not sidebar-exposed: it is neutral and temperature-0 by contract. When a v1-only tab eventually lands, the whole expander can be hidden conditionally without moving the widgets.
- **Creative page tabs** — `frontend/pages/creative.py` is split into two tabs via `st.tabs`: `c1_territory` (default, left) runs the Standard 2.0 Creative 1 territory-generation agent and renders results via `components.territory_cards.render_territory_cards()`; `c0_original` (right) runs the original Standard 1.0 creative agent unchanged. Each tab owns its own session-state keys (`c1_brief_input`/`c1_result` vs `creative_brief_input`/`creative_result`) so switching tabs never wipes the other tab's work. `num_territories` is a per-page control (1–12 via `st.number_input`) on the `c1_territory` tab — it is not sidebar-exposed because only this page and Phase E's Workflow v2 tab will consume it. When Phase E lands, the Workflow page will follow the same tabbed structure (Standard 2.0 default, Standard 1.0 right) and can reuse `render_territory_cards()` for its territory-selection interrupt UI.
- Configurable thresholds live in `config.py` and are read via `_get_secret()`: `MAX_ITERATIONS` (default 3), `APPROVAL_THRESHOLD` (default 80.0), `LLM_MAX_RETRIES` (default 3), and `DEMO_RUN_CAP` (default 10). All four are overridable via env var or Streamlit secret.

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
- `.archive/` — contains snapshots, backups, completed one-off specs, and completed workplans, not working code. Never read from or execute anything in this directory. Specifically:
  - `.archive/specs/` — completed feature specs (design documents that have been implemented)
  - `.archive/workplans/` — completed execution plans (operational plans whose work is done and whose ADR is committed)