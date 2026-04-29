# agt_sea — AI Creative Agency Framework

Three AI agents (Strategist, Creative, Creative Director) collaborate via LangGraph to transform a client brief into a creative campaign concept. Provider-switchable (Anthropic/Google/OpenAI). Deployed on Streamlit Cloud.

See `README.md` for full project overview, project structure tree, and architecture diagram. Decisions referenced as `(see ADR 00XX)` live in `docs/adr/`.

## Commands

```bash
uv sync                                    # Install dependencies
uv pip install -e .                        # Make agt_sea importable
uv run streamlit run frontend/app.py       # Run frontend locally
uv run python tests/test_pipeline_st1.py   # Full Standard 1.0 pipeline test (real LLM calls)
uv run python -i tests/test_pipeline_st1.py # Interactive — explore final_state after run
uv run python tests/test_strategist_st1.py # Strategist (Standard 1.0) only
uv run python tests/test_strategist_st2.py # Strategist (Standard 2.0) only
uv run python tests/test_creative_st1.py   # Strategist + Creative (Standard 1.0)
uv run python tests/test_creative_a_st2.py # Strategist + Creative A (Standard 2.0)
uv run python tests/test_creative_b_st2.py # Strategist + Creative A + Creative B (Standard 2.0)
uv run python tests/test_pipeline_st2.py   # Full Standard 2.0 pipeline — pauses at interrupt, auto-selects territory[0]
uv run ruff check .                        # Lint
uv run pytest tests/                       # Unit tests (excludes manual integration scripts)
```

## Tech Stack

- Python 3.11+, managed with uv
- LangGraph for orchestration, LangChain for LLM abstraction
- Pydantic for data models and structured output (`with_structured_output()`)
- Streamlit for frontend, deployed to Streamlit Cloud
- Default LLM: Anthropic (claude-sonnet-4-6), switchable via `LLM_PROVIDER` env var or sidebar selector

## Code Style

- `from __future__ import annotations` at top of all modules
- Type hints on all function signatures and return types
- Docstrings on all modules and functions
- One function, one job

## Architecture Rules — IMPORTANT

- All agents import LLM via `from agt_sea.llm.provider import get_llm` — never instantiate models directly
- State flows through `AgencyState` (Pydantic) — agents read what they need, update fields, append to `history`
- Routing functions are pure: return strings only, NEVER mutate state. State changes before END happen in dedicated finalisation nodes
- Pass-through nodes are allowed where a conditional edge needs a source node but no state mutation (e.g. `check_iterations` is `lambda state: state`)
- **LangGraph boundary — Pydantic in, dict out (rehydrate at the edge).** `graph.invoke()` / `graph.stream()` accept `AgencyState` but return plain dicts. Every call site must rehydrate with `AgencyState.model_validate(raw)` before attribute access — never `.get()` or `state["field"]`. For `stream()`, accumulate per-node updates into a running dict first, then rehydrate once at the end. Same rule on v1 and v2 — after a v2 interrupt, read paused state via `graph.get_state(cfg).values` and rehydrate the same way. Canonical patterns in `frontend/pages/workflow.py` and `tests/test_pipeline_st1.py` (see ADR 0011)
- `config.py` uses `_get_secret()` (env first, then `st.secrets`); API keys are bridged from `st.secrets` → `os.environ` at module load so LangChain providers find them
- `get_llm()` accepts optional `provider`, `model`, `temperature`. `temperature: float | None` — when `None` the argument is omitted and the provider's server-side default applies. Standard 1.0 agents pass `temperature=0.7` explicitly; Standard 2.0 agents read per-agent temperature from `AgencyState`
- **Temperature resolution idiom (every new agent).** Temperature lives on `AgencyState` per-agent, not as an `_AGENT_TEMPERATURE` constant. New agents read it as `state.<agent>_temperature` and pass through to `get_llm(temperature=...)`. The grader is the existence proof that even hardcoded values (0.0 for repeatable scoring) belong on state — recorded run metadata then matches the actual call.
- **Neutral-skip pattern (every prompt-injection lens).** When a lens enum value is `NEUTRAL`, the corresponding `load_*()` is skipped and the prompt section stays empty — the prompt reads as if the feature wasn't there at all. Applies uniformly to philosophy, provenance, and taste. Any future injection category must follow the same convention.
- Selectable model lists live in `config.AVAILABLE_MODELS` (one per provider). Sidebar imports from there — don't redefine in `frontend/components/sidebar.py`. Any provider's `DEFAULT_MODELS` entry must appear in its `AVAILABLE_MODELS` list
- Per-agent philosophy fields on `AgencyState` (all default `NEUTRAL`, sidebar mirrors to `st.session_state`):
  - **Standard 1.0:** `strategist_st1_strategic_philosophy`, `creative_st1_creative_philosophy`, `creative_director_st1_creative_philosophy`
  - **Standard 2.0:** `strategist_st2_strategic_philosophy`, `creative_a_st2_creative_philosophy`, `creative_b_st2_creative_philosophy`, `creative_director_st2_creative_philosophy` (shared by CD Feedback + CD Synthesis; CD Grader is neutral by contract — no field)
  - Every page that builds `AgencyState` must pass through the philosophies its target pipeline consumes
- **Standard 2.0 data model** — adds `Territory`, `CampaignDeliverable`, `CampaignConcept`, `GraderEvaluation`, `ConceptScoreSummary`, `CDSynthesis` to `models/state.py`, plus enums `Provenance` and `Taste` (each with `NEUTRAL` + presets — see `models/state.py` for values). Prompt content lives as one `.txt` per non-NEUTRAL value in `prompts/provenance/` and `prompts/taste/`, loaded via `load_provenance()` / `load_taste()`. v1 files untouched; v2 lives in separate files (see ADR 0014)
- **Per-role lenses on `AgencyState`** — provenance + taste scoped per *creative role*: `creative_a_st2_*`, `creative_b_st2_*`, and shared `creative_director_st2_*` (CD Feedback + CD Synthesis). All default to `NEUTRAL`. CD Grader is always neutral by contract — never inject philosophy/provenance/taste into it
- **Per-agent temperature on `AgencyState`** — `creative_a_st2_temperature`, `creative_b_st2_temperature`, `cd_feedback_st2_temperature`, `cd_synthesis_st2_temperature` (default `0.7`); `cd_grader_st2_temperature` (default `0.0`, not sidebar-exposed). All bounded `0.0–1.0`. Lives in the `# --- Iteration tracking ---` block
- **Standard 2.0 agent-output fields** — `territories`, `num_territories` (default 3, bounded 1–12), `selected_territory`, `territory_rejection_context`, `campaign_concept`, `grader_evaluation`, `cd_feedback_direction`, `cd_synthesis`. Live in the existing `# --- Agent outputs ---` block with a `# [2.0]` marker
- **Structured output for list-valued schemas — wrapper model required.** `with_structured_output()` rejects bare `list[Territory]`. Define a module-local wrapper (e.g. `class TerritorySet(BaseModel): territories: list[Territory]`), pass it to `with_structured_output()`, unwrap before writing to state. Don't add wrappers to `models/state.py`
- **Agent input contract is agent-scoped, not caller-scoped.** When an agent reads an optional state field, it reads it regardless of caller — graph, page, test, future caller
- **State organisation — don't segregate by workflow version.** `AgencyState` is one object shared by 1.0 and 2.0. Extend existing groups (`Input`, `LLM overrides`, `Agent outputs`, `Iteration tracking`, `History`, `Workflow`); a `# [2.0]` marker is fine, a top-level version split is not
- **Safe-node wrapper** — every agent node is wrapped with `_safe_node()` at graph-build time. Don't add `try`/`except` inside agent functions. Standalone pages calling agents directly (e.g. `frontend/pages/strategy.py`, `frontend/pages/creative.py`) must use `format_node_error(fn_name, exc)` to construct `state.error` (see ADR 0012). v2 has its own `_safe_node` that re-raises `GraphBubbleUp` so `interrupt()` works
- **Failure contract** — `WorkflowStatus.FAILED` and `state.error` are the contract between graph and frontend. Routing diverts to `finalise_failed → END`. Frontend pages check `state.status == WorkflowStatus.FAILED` after rehydration. Routers begin with `if state.error is not None: return "failed"` (see ADR 0012)
- **No `WorkflowStatus` value mirrors "paused".** The authoritative pause signal is LangGraph's own (`graph.get_state(config).interrupts`). Don't add a `PAUSED` enum value

## V2 Workflow Conventions

The Standard 2.0 pipeline is a multi-stage workflow with one human-in-the-loop interrupt and a fan-out CD role. Most rules already exist above — this section collects the v2-specific patterns in one place so they read end-to-end.

**Agent signatures (Standard 2.0).** Same shape as Standard 1.0 (`def run_<agent>(state: AgencyState) -> AgencyState`), but each agent's `_build_system_prompt()` helper accepts the relevant lenses:
- Creative A (`creative_a_st2`): `_build_system_prompt(philosophy, provenance, taste, num_territories)` — count interpolated, never hardcoded.
- Creative B (`creative_b_st2`): `_build_system_prompt(...)` + `_build_revision_prompt(...)` — two prompt paths gated on `state.grader_evaluation` + `state.cd_feedback_direction`.
- CD Grader (`cd_grader_st2`): `_build_system_prompt()` (no parameters) — neutral by contract; never inject philosophy/provenance/taste.
- CD Feedback (`cd_feedback_st2`): `_build_system_prompt(philosophy, provenance, taste)` + `_build_human_message(...)` — free-text output.
- CD Synthesis (`cd_synthesis_st2`): `_build_system_prompt(philosophy, provenance, taste)` — structured `CDSynthesis`.

**Interrupt / resume pattern.** Pauses at `interrupt_territory_selection`. Resume value contract is `{"action": "select", "index": int}` to develop a territory or `{"action": "rerun", "rejection_context": str | None}` to regenerate. Pass `Command(resume=<value>)` from `langgraph.types` as the input to the next `stream()` / `invoke()` call on the same `thread_id`. The interrupt node is **idempotent** — re-executes from the top on every resume, so do not write history, bump counters, or call LLMs inside it.

**Checkpointer.** Module-scope `_CHECKPOINTER = MemorySaver()` in `workflow_v2.py`. Every `build_graph_v2()` call shares the same instance, so Streamlit's per-interaction script reruns don't drop in-flight interrupts. `MemorySaver` does not survive a process restart — persistent checkpointing (SQLite/Postgres) is the upgrade path.

**Thread config.** Mandatory on every `agency_graph_v2.invoke(...)` / `.stream(...)` / `.get_state(...)` call. Same `thread_id` links the initial run to every resume.

**Per-role vs per-agent injection scoping.** Two different scopings on `AgencyState`:
- **Per-role (philosophy, provenance, taste):** scoped to the *creative role* — `creative_a_st2_*`, `creative_b_st2_*`, `creative_director_st2_*` (CD pair shared by Feedback and Synthesis).
- **Per-agent (temperature):** scoped to each *agent* individually — `creative_a_st2_temperature`, `creative_b_st2_temperature`, `cd_feedback_st2_temperature`, `cd_synthesis_st2_temperature`, `cd_grader_st2_temperature`.

Don't conflate them. Provenance/taste are creative-identity lenses (a CD has one identity for both its feedback and synthesis voice); temperature is a per-call generation knob (Feedback wants creative latitude, Synthesis wants confidence, both differ from each other).

**Territory data model.** `Territory` is an atomic, modular block (`title`, `core_idea`, `why_it_works` — no execution detail). `list[Territory]` lives on state. `selected_territory: Territory | None` is the user's pick. Territory count `num_territories` is bounded `1–12` on state and is *not* sidebar-exposed — it lives on the Creative page tab and the workflow page uses the default. Territories are interchangeable and parallelisable by design (the future N× Creative 2 variant requires no state rearchitect).

**Campaign concept structure.** `CampaignConcept` (`title`, `core_idea`, `deliverables: list[CampaignDeliverable]`, `why_it_works`) is Creative B's structured output. Each `CampaignDeliverable` is `name` + `explanation`. Always produced via `with_structured_output()` + `invoke_with_validation_retry`.

**CD role split — campaign-scoped, not territory-scoped.** All three CD agents (Grader, Feedback, Synthesis) operate on `state.campaign_concept`. Territories are handled by the human at the interrupt — no CD agent evaluates or coaches on territories. Their separation:
- Grader = *measurement* (objective score, temp 0.0, no injection, lean schema).
- Feedback = *coaching* (free-text revision direction, temp configurable, full injection, fires only on the rejection-with-budget path).
- Synthesis = *recommendation* (structured `CDSynthesis`, temp configurable, full injection, fires once before END on both approved and exhausted paths).

**Synthesis as the user-facing voice.** CD Synthesis is the output the user reads — written as confident recommendation, not review. `CDSynthesis.comparison_notes` stays `None` when only one concept is present (the simplified v2 graph), populated when multiple are (the future parallel variant).

**Failure path is identical to v1.** `WorkflowStatus.FAILED` and `state.error`, `_safe_node` wrapper at graph-build time, `_check_failed` routing guard at the top of every router, `finalise_failed → END`. The only v2 deviation is that `_safe_node` re-raises `GraphBubbleUp` so `interrupt()` works.

**Run metadata for reproducibility.** Per-agent temperature values live on `AgencyState` (rather than as in-agent constants) specifically so the `AgentOutput` history records the value that was actually used for each call. When adding a future agent with non-default temperature, follow the same pattern.

## Agent Conventions

- Each agent function signature: `def run_agent(state: AgencyState) -> AgencyState`
- Each agent must: call `get_llm()`, update relevant state fields, append `AgentOutput` to `state.history`
- Each agent resolves provider/model as: `state.llm_provider or get_llm_provider()` and `state.llm_model or get_model_name(provider)` — sidebar overrides reach agents via `AgencyState.llm_provider` / `AgencyState.llm_model`
- `AgentOutput` must include: `agent`, `provider`, `model`, `iteration`, `content`, `timestamp`
- Creative Director (1.0) uses `llm.with_structured_output(CDEvaluation)` for validated scoring; Creative (1.0) checks `state.cd_evaluation is not None` to determine initial vs revision path
- **Philosophy injection pattern (Standard 1.0).** Strategist, Creative, and Creative Director each build their system prompt via `_build_system_prompt(philosophy)` (Creative also has `_build_revision_prompt`). Each follows the neutral-skip rule. Strategist reads `state.strategist_st1_strategic_philosophy`, Creative reads `state.creative_st1_creative_philosophy`, CD reads `state.creative_director_st1_creative_philosophy`
- Standard 2.0 agent helpers (`_build_system_prompt(...)` shapes per agent) are detailed in **V2 Workflow Conventions** above
- **Validation retry helper is shared.** `invoke_with_validation_retry` lives in `agt_sea/llm/provider.py`, generic over any Pydantic model. Use it (not the structured runnable directly) in every agent that uses `with_structured_output()` — Creative A, Creative B, Creative Director, CD Grader, CD Synthesis
- Strategist prompts are assembled via `load_template()` (structural scaffold) and `load_guidance()` (technique-specific guidance) — don't hardcode the brief template or proposition guidance inline
- **Logging** — agents use stdlib `logging`. Module-level `logger = logging.getLogger(__name__)`; `logger.warning()` for recoverable anomalies, `logger.error()` for failures
- **Run guard** — every agent-invoking frontend page must call `check_run_allowed()` from `frontend/components/run_guard.py` before constructing `AgencyState`. If `False`, render `render_run_limit_reached()` and `st.stop()`. Cap is `config.DEMO_RUN_CAP` (default 10) (see ADR 0013)

## Workflow Rules

- Run tests after changes to agents or graph logic
- `uv run pytest tests/` runs unit tests only — `pyproject.toml` ignores manual real-LLM integration scripts (`test_strategist_st1`, `test_strategist_st2`, `test_creative_st1`, `test_creative_a_st2`, `test_creative_b_st2`, `test_pipeline_st1`, `test_pipeline_st2`). Run those directly with `uv run python tests/test_<name>.py`. The `test_cd_grader_st2` and `test_cd_synthesis_st2` files are pytest unit tests and run as part of the default suite
- Run `ruff check .` before committing
- Commit messages: imperative mood, conventional commits (`feat:`, `fix:`, `chore:`, `docs:`)
- ADRs are append-only — new decisions get new numbered files. The one exception is updating the `Status:` line of an older ADR to flag supersession (e.g. ADR 0006 → 0007, ADR 0003 → 0011)
- Workplans live at `docs/workplans/`, specs at `docs/specs/`. When work is complete and the ADR is committed, `git mv` to `.archive/workplans/` or `.archive/specs/`. ADRs are the durable artefact
- When adding a new agent, follow the pattern in `agents/strategist_st1.py` (or `strategist_st2.py`)
- Explain reasoning before changes — what, why, alternatives considered
- When introducing a new pattern, explain it as if teaching a mid-level developer

## Deployment

- Streamlit Cloud auto-deploys from main; `frontend/app.py` has `sys.path.insert` at top to resolve `agt_sea` imports on Cloud. Page files loaded via `st.Page()` run in the same process
- API keys and config overrides go in Streamlit Cloud secrets dashboard, not `.env`. Per-provider model secrets (`ANTHROPIC_MODEL`, `GOOGLE_MODEL`, `OPENAI_MODEL`) override defaults on Cloud for cost control
- `.streamlit/config.toml` pins `base = "light"`. All visual styling comes from `b3ta.css`
- `app.py` initialises session state defaults via `setdefault` before the sidebar renders, so pages never hit a missing key
- **Sidebar scope** — top-level controls (provider, model, max iterations, approval threshold). Per-agent philosophy selectors live in two collapsed expanders: `STANDARD 1.0 CONTROLS` (3 selectors — strategist, creative, creative director) and `STANDARD 2.0 CONTROLS` (4 philosophies — strategist, creative_a, creative_b, creative_director — plus per-role provenance + taste and per-agent temperature). CD Grader is not sidebar-exposed: neutral and temp-0 by contract
- **Creative page tabs** — `frontend/pages/creative.py` has two tabs: `st2_territory` (default) runs Creative A with `render_territory_cards()`; `st1_campaign` runs Standard 1.0's creative agent unchanged. Each tab owns its own session-state keys (`st2_brief_input`/`st2_result` vs `st1_brief_input`/`st1_result`). `num_territories` (1–12) is per-page on `st2_territory`, not sidebar-exposed
- **Workflow page tabs** — `frontend/pages/workflow.py` has two tabs: `Standard 2.0` (default, runs v2 graph) and `Standard 1.0` (lifted verbatim into `_render_standard_v1()` — do not edit when extending v2). Each tab owns its own session-state keys
  - **v1 keys:** `workflow_brief_input`, `workflow_result`
  - **v2 keys:** `v2_brief_input` (persisted brief); `v2_thread_id` (UUID per run, links initial invoke + every resume through the module-scope `MemorySaver`); `v2_phase: "idle" | "interrupted" | "terminal"` (UI-dispatch state machine, enumerated explicitly — no implicit None-fourth-state; derived from checkpointer snapshot via `_v2_update_phase_from_graph()` after every stream call); `v2_pending_action` (deferred-stream queue — buttons set, handler pops atomically with `st.session_state.pop(...)` to prevent re-render double-consumption; mapped to a `Command(resume=...)` or fresh initial stream); `v2_selected_territory_preview` (UI bridge between click and resume-stream completion). `_reset_v2_session()` clears all v2 keys
  - **Persistent run-context block (`_render_v2_persistent_brief`)** renders below RUN button between two horizontal dividers regardless of phase. Sources from the checkpointer (not session_state) so it survives every rerun for the run's `thread_id`
  - **Stream-end rerun (`st.rerun()`)** is called after every v2 stream and the v1 stream — streaming widgets are visible only DURING active streaming
  - **Two concerns during streaming stay separate.** Per-node `stream()` events feed `render_node_progress()` only (ephemeral UI). Authoritative state for territory-selection and terminal renders is `agency_graph_v2.get_state(cfg).values` rehydrated. v1 accumulates per-node events because it has no checkpointer; v2 doesn't — checkpointer is the source of truth
  - **Extended components.** `progress.py` carries v2 node labels/previews (compact for `creative_b_st2`/`cd_feedback_st2`/`cd_synthesis_st2`; full audit detail lives in pipeline history at terminal). `history.py` handles every `AgentRole` (v1: `STRATEGIST_ST1`, `CREATIVE_ST1`, `CREATIVE_DIRECTOR_ST1`; v2: `STRATEGIST_ST2`, `CREATIVE_A_ST2`, `CREATIVE_B_ST2`, `CD_GRADER_ST2`, `CD_FEEDBACK_ST2`, `CD_SYNTHESIS_ST2`) with iteration counters scoped per-role. `synthesis_output.py` is the v2-only terminal renderer for `CDSynthesis` + `CampaignConcept`. `territory_cards.py` exposes both `render_territory_cards()` (bordered grid) and `render_territory_body()` (boundary-free, reused by the selected-territory expander)
- Configurable thresholds in `config.py` via `_get_secret()`: `MAX_ITERATIONS` (3), `APPROVAL_THRESHOLD` (80.0), `LLM_MAX_RETRIES` (3), `DEMO_RUN_CAP` (10). All overridable via env or Streamlit secret

## Current Phase & Roadmap

**Current:** MODULE 01) Phase 6 — Refinement (error handling, frontend refinement, human-in-the-loop, logging/tracing)

Frontend is a multipage Streamlit app with `st.navigation()`. Modules planned: 1) Workflows (COMPLETE, deployed), 2) Strategy (COMPLETE), 3) Creative (COMPLETE), 4) Tools (page visible with holding message), 5) Marketing / 6) Production / 7) Agnostic (placeholder pages, hidden).

## Ignore these directories

- `.archive/` — snapshots, backups, completed specs and workplans, not working code. Never read from or execute anything in this directory:
  - `.archive/specs/` — completed feature specs
  - `.archive/workplans/` — completed execution plans
