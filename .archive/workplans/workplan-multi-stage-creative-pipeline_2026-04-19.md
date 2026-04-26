# Workplan: Multi-Stage Creative Pipeline (ADR 0014)

**Date:** 2026-04-19
**Target:** Standard 2.0 workflow + Creative 1 standalone page

## Overview

Implement the multi-stage creative pipeline described in ADR 0014. Eight phases, each producing a testable increment. Phases are ordered so that Creative 1 is user-testable on the standalone Creative page before the full v2 workflow is built.

## Phases

### Phase A — ADR + State Model Foundations

**Goal:** Lock the architecture decision, extend the data model.

**Files touched:**
- `docs/adr/0014-multi-stage-creative-pipeline.md` — new ADR
- `docs/adr/README.md` — add 0014 to index
- `src/agt_sea/models/state.py` — new models and fields

**State model changes:**

New models:
- `Territory(BaseModel)` — `title: str`, `core_idea: str`, `why_it_works: str`
- `CampaignConcept(BaseModel)` — `title: str`, `core_idea: str`, `deliverables: list[CampaignDeliverable]`, `why_it_works: str`
- `CampaignDeliverable(BaseModel)` — `name: str`, `explanation: str`
- `GraderEvaluation(BaseModel)` — `score: float` (0–100, validated), `rationale: str`
- `CDSynthesis(BaseModel)` — `selected_title: str`, `recommendation: str`, `score_summary: list[ConceptScoreSummary]`, `comparison_notes: str | None = None`
- `ConceptScoreSummary(BaseModel)` — `title: str`, `score: float`, `assessment: str`

New enums:
- `Provenance(str, Enum)` — `NEUTRAL` + 3 presets (placeholder names until content is written)
- `Taste(str, Enum)` — `NEUTRAL` + 3 presets

New fields on `AgencyState`:
- `territories: list[Territory] = Field(default_factory=list)` — Creative 1 output
- `num_territories: int = Field(default=3, ge=1, le=10)` — configurable territory count
- `selected_territory: Territory | None = None` — user's pick after interrupt
- `territory_rejection_context: str | None = None` — optional user feedback when rerunning Creative 1
- `campaign_concept: CampaignConcept | None = None` — Creative 2 output (structured: title, core idea, deliverables, rationale)
- `grader_evaluation: GraderEvaluation | None = None` — latest grader score
- `cd_synthesis: CDSynthesis | None = None` — final synthesis output
- Per-role provenance/taste: `creative1_provenance`, `creative1_taste`, `creative2_provenance`, `creative2_taste`, `cd_provenance`, `cd_taste` (all enum type, default `NEUTRAL`)
- Per-agent temperature: `creative1_temperature`, `creative2_temperature`, `cd_feedback_temperature`, `cd_synthesis_temperature` (all `float = 0.7`)
- `grader_temperature: float = 0.0` — hardcoded default, not sidebar-exposed but on state for traceability

**CLAUDE.md updates:** Add new models, enums, and fields to the relevant sections.

**Test:** State model instantiation, validation constraints (territory count bounds, score bounds), enum values.

---

### Phase B — Infrastructure: Prompts, Temperature, Provenance/Taste

**Goal:** Prompt files, loader wrappers, temperature support in `get_llm()`, sidebar extensions.

**Files touched:**
- `src/agt_sea/prompts/provenance/` — 3 placeholder `.txt` files + directory
- `src/agt_sea/prompts/taste/` — 3 placeholder `.txt` files + directory
- `src/agt_sea/prompts/loader.py` — `load_provenance()`, `load_taste()` wrappers
- `src/agt_sea/models/state.py` — enum values updated if placeholder names change
- `src/agt_sea/llm/provider.py` — `temperature` parameter on `get_llm()`
- `frontend/components/sidebar.py` — provenance/taste selectors, temperature sliders
- `frontend/app.py` — session state defaults for new fields

**Temperature in `get_llm()`:** Add `temperature: float | None = None` parameter. When not `None`, pass to `ChatAnthropic(temperature=...)` / `ChatGoogleGenerativeAI(temperature=...)` / `ChatOpenAI(temperature=...)`. Verify each provider's constructor accepts this. The `wrap_with_transport_retry()` call happens after temperature is set — no interaction.

**Sidebar layout:** Group the new controls sensibly. Likely under collapsible expanders per role ("Creative 1 settings", "Creative 2 settings", "Creative Director settings"). Provenance/taste selectors + temperature slider per group. The v2 controls should only be visible when the v2 tab is active (or could show always — decision at implementation time based on what feels right in the UI).

**Test:** `load_provenance()` / `load_taste()` return expected content, `get_llm(temperature=0.0)` produces a model with temp=0, `get_llm(temperature=None)` uses provider default.

---

### Phase C1 — Creative 1 Agent

**Goal:** Territory generation agent, testable in isolation.

**Files touched:**
- `src/agt_sea/agents/creative1.py` — new agent
- `tests/test_creative1.py` — manual integration test (real LLM calls)

**Agent contract:**
- Input: `AgencyState` with `creative_brief` populated, plus `creative1_provenance`, `creative1_taste`, `creative1_temperature`, `num_territories`, `creative_philosophy`
- Output: `AgencyState` with `territories: list[Territory]` populated (length = `num_territories`), `AgentOutput` appended to history
- Prompt: `_build_system_prompt(philosophy, provenance, taste)` — extends the existing pattern with provenance/taste sections
- LLM call: `get_llm(provider=..., model=..., temperature=state.creative1_temperature)` with `with_structured_output()` to enforce the territory list schema
- Structured output: need to confirm whether `with_structured_output()` works cleanly with `list[Territory]` or whether a wrapper model is needed (e.g. `TerritorySet(BaseModel): territories: list[Territory]`)

**Test:** Run against a sample brief, verify 3 territories returned, each with non-empty title/core_idea/why_it_works.

---

### Phase C-FE — Creative Page Tabs (Creative 1 Standalone)

**Goal:** Users can test territory generation in isolation on the Creative page.

**Files touched:**
- `frontend/pages/creative.py` — add tabs, wire Creative 1 to `c1_territory` tab
- `frontend/components/sidebar.py` — possibly minor adjustments for standalone creative context

**Tab structure:**
- `c1_territory` (default, left) — uses Creative 1 agent. Displays territory cards. Num territories selector (1–10). Provenance/taste/temperature/philosophy controls for Creative 1.
- `c0_original` (right) — current creative page functionality, unchanged.

**Territory display:** Each territory rendered as a distinct card/block — title, core idea, why it works. Modular layout that communicates these are independent options.

**Run guard:** Both tabs use `check_run_allowed()` — existing pattern.

**Test:** Manual — run Creative 1 from the UI, verify territories display as separate blocks.

---

### Phase C2 — Remaining New Agents

**Goal:** Creative 2, CD Grader, CD Feedback, CD Synthesis agents.

**Files touched:**
- `src/agt_sea/agents/creative2.py`
- `src/agt_sea/agents/cd_grader.py`
- `src/agt_sea/agents/cd_feedback.py`
- `src/agt_sea/agents/cd_synthesis.py`
- `tests/test_creative2.py` — manual integration test
- `tests/test_cd_grader.py` — unit test (structured output validation)

**Creative 2 contract:**
- Input: `AgencyState` with `selected_territory` populated, plus `creative_brief`, provenance/taste/temp for creative2
- Output: `campaign_concept: CampaignConcept` (structured via `with_structured_output(CampaignConcept)`), `AgentOutput` appended to history
- Revision path: when `grader_evaluation` is not None and `cd_feedback_direction` is not None, incorporate feedback (same pattern as current creative's revision path)

**CD Grader contract:**
- Input: `AgencyState` with `campaign_concept` populated
- Output: `grader_evaluation: GraderEvaluation` (score + rationale), `AgentOutput` appended to history
- Temperature: always 0, no philosophy/provenance/taste injection
- Schema: `with_structured_output(GraderEvaluation)`

**CD Feedback contract:**
- Input: `AgencyState` with `campaign_concept`, `grader_evaluation`, `creative_brief`
- Output: `cd_feedback_direction: str` on state (qualitative revision direction for Creative 2), `AgentOutput` appended to history
- Temperature: `state.cd_feedback_temperature`
- Philosophy/provenance/taste: injected from `state.cd_provenance`, `state.cd_taste`, `state.cd_philosophy`

**CD Synthesis contract:**
- Input: `AgencyState` with `campaign_concept`, `grader_evaluation`, full history
- Output: `cd_synthesis: CDSynthesis`, `AgentOutput` appended to history
- Temperature: `state.cd_synthesis_temperature`
- Philosophy/provenance/taste: injected
- Schema: `with_structured_output(CDSynthesis)`
- Prompt: built to evaluate N concepts even though v1 passes 1

**New field on AgencyState** (add in this phase): `cd_feedback_direction: str | None = None`

**Test:** Each agent in isolation with fixture state. CD Grader specifically tested for score validation (0–100 constraint on `GraderEvaluation`).

---

### Phase D — Graph: v2 Workflow with Interrupt

**Goal:** New LangGraph graph definition with territory selection interrupt and campaign iteration loop.

**Files touched:**
- `src/agt_sea/graph/workflow_v2.py` — new graph definition
- `tests/test_pipeline_v2.py` — integration test (real LLM calls, simulated territory selection)

**Graph nodes:**
1. `strategist` — existing agent, wrapped with `_safe_node()`
2. `creative1` — territory generation, wrapped
3. `interrupt_territory_selection` — `interrupt()` call, pauses graph. User input (selected territory + optional rejection context) provided on resume.
4. `creative2` — campaign development, wrapped
5. `cd_grader` — scoring, wrapped
6. `check_approval` — pass-through node for conditional routing
7. `cd_feedback` — revision direction, wrapped (only on rejection path)
8. `cd_synthesis` — final evaluation, wrapped
9. `finalise_approved` — sets status, fires before END on approval path
10. `finalise_max_iterations` — sets status, selects best-of, fires before END on exhaustion path
11. `finalise_failed` — sets status on error, fires before END

**Routing:**
- After creative1 → interrupt
- After interrupt → creative2 (or back to creative1 if user chose rerun — need to model this)
- After cd_grader → check_approval
- check_approval routing: approved → cd_synthesis, rejected + budget → cd_feedback, rejected + exhausted → cd_synthesis (best-of)
- All routing functions: error guard at top (`if state.error is not None: return "failed"`)

**Checkpointer:** `MemorySaver` instantiated in `workflow_v2.py` and passed to `StateGraph.compile(checkpointer=...)`.

**Rerun logic:** When the user chooses to rerun Creative 1 instead of selecting a territory, the graph needs to loop back to `creative1`. Model this as a conditional edge from the interrupt node: if `selected_territory` is populated → `creative2`, if not (rerun) → `creative1`. The `territory_rejection_context` is available to Creative 1 on the rerun.

**Test:** Full pipeline run with a simulated territory selection at the interrupt point. Verify final state has `cd_synthesis` populated and correct status.

---

### Phase E — Workflow Page: Standard 2.0 / 1.0 Tabs

**Goal:** New workflow tab running the v2 graph, existing workflow as v1 tab.

**Files touched:**
- `frontend/pages/workflow.py` — add tabs, territory selection UI, wire v2 graph
- `frontend/components/` — possibly new components for territory selection cards, grader display, synthesis display

**Tab structure:**
- "Standard 2.0" (default, left) — runs `workflow_v2` graph. Includes territory selection interrupt UI.
- "Standard 1.0" (right) — current workflow, unchanged.

**Territory selection UI:** After Creative 1 completes and the graph interrupts, display territory cards with a "Select" button on each, plus a "Generate new territories" button with an optional text input for rejection context. On selection, resume the graph with the chosen territory.

**Progress display:** Adapted for v2 stages — strategist, creative 1, (interrupt), creative 2, grader, (possible feedback loop), synthesis.

**Streaming/rehydration:** Same boundary pattern as v1 — `AgencyState.model_validate()` after graph output. The interrupt/resume pattern may require adjustments to how streaming events are accumulated.

---

### Phase F — Polish, Testing, Documentation

**Goal:** End-to-end testing, documentation updates, cleanup.

**Tasks:**
- End-to-end testing across providers (Anthropic, Google, OpenAI)
- README.md update with new architecture diagram (mermaid for v2 flow)
- CLAUDE.md final update — new agent conventions, v2 graph patterns, interrupt/resume pattern
- ADR index update (already done in Phase A, verify)
- `architecture.md` updated or new `architecture_v2.md` added
- Ruff clean, all tests green
- Workplan moved to `.archive/workplans/`

---

## Phase dependency graph

```
A (state model) → B (infra) → C1 (creative 1 agent) → C-FE (creative page tabs)
                            ↘
                             C2 (remaining agents) → D (graph v2) → E (workflow tabs) → F (polish)
```

C1 and C-FE can ship independently of C2/D/E. After C-FE, users can test territory generation while the rest of the pipeline is built.

## Claude Code session guidance

- **Phase A:** Small, focused. Read CLAUDE.md + `models/state.py` + this workplan. Output: ADR file, state model changes, CLAUDE.md updates.
- **Phase B:** Read CLAUDE.md + `prompts/loader.py` + `llm/provider.py` + `frontend/components/sidebar.py` + `frontend/app.py`. Output: prompt files, loader wrappers, temperature support, sidebar changes.
- **Phase C1:** Read CLAUDE.md + `agents/creative.py` (for pattern reference) + `models/state.py`. Output: new agent file + test.
- **Phase C-FE:** Read CLAUDE.md + `frontend/pages/creative.py` + `frontend/components/`. Output: tabbed creative page.
- **Phase C2:** Read CLAUDE.md + `agents/creative1.py` (just built) + `agents/creative_director.py` (for CD pattern reference) + `models/state.py`. Output: 4 new agent files + tests.
- **Phase D:** Read CLAUDE.md + `graph/workflow.py` (v1 reference) + all new agents + `models/state.py`. This is the largest session — may need to split if context gets tight.
- **Phase E:** Read CLAUDE.md + `frontend/pages/workflow.py` + `graph/workflow_v2.py` + `frontend/components/`. Output: tabbed workflow page with territory selection UI.
- **Phase F:** Sweep. Read CLAUDE.md + README.md. Output: docs, cleanup.

## Risk notes

- **LangGraph interrupt/resume:** First use in the project. Phase D should include a minimal spike to validate the interrupt pattern works with Streamlit before building the full graph. If it doesn't work cleanly with Streamlit's execution model, the fallback is the two-run approach (Phase C-FE already demonstrates the territory display).
- **Structured output for list[Territory]:** Confirm in Phase C1 whether `with_structured_output()` handles `list[Territory]` or needs a wrapper model. Test early.
- **Sidebar complexity:** Phase B adds substantial sidebar surface. May need a "v2 settings" collapsible section or similar to keep the UI manageable.