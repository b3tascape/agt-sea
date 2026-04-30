# ADR 0014: Multi-Stage Creative Pipeline with Territory Selection

**Status:** Accepted (renamed under st1/st2 convention; see CLAUDE.md)
**Date:** 2026-04-19
**Extends:** [ADR 0006](0006-iterative-loop-design.md) (new workflow variant with different loop structure), [ADR 0010](0010-prompt-injection-pattern.md) (new prompt injection categories)

## Context

The v1 creative workflow (Standard 1.0) runs a single creative agent that generates a full campaign concept, evaluated by a single Creative Director in a tight loop. This has two structural limitations:

1. **The creative agent does too much in one shot.** It generates a campaign title, core idea, execution details, and rationale all at once. The output is broad but shallow — the LLM spreads its attention across format, execution, and strategy simultaneously rather than going deep on the core idea first. In practice, the strongest part of any creative output is the central thought; execution details are easier to develop once the idea is locked.

2. **The Creative Director conflates scoring with feedback.** A single agent at a single temperature produces both a numeric score (which should be consistent and objective) and qualitative revision direction (which benefits from creative latitude and philosophical perspective). These are different cognitive tasks with different temperature requirements. Bundling them means the score is influenced by the CD's creative temperature, and the feedback is constrained by the structured output schema.

3. **No human input on creative direction.** The system generates one concept and iterates on it autonomously. The user has no opportunity to steer which creative territory gets developed — they see only the final output. For a tool aimed at creative professionals, this removes the most important decision point: choosing which idea to back.

4. **No separation of concerns for prompt injection.** Philosophy is the only lens available. Real creative work is shaped by the practitioner's background, tastes, and influences — not just an abstract methodology. The prompt injection system (ADR 0010) supports adding new categories, but the agent architecture doesn't yet have the fields or sidebar controls to use them.

## Decision

### 1. Two-stage creative pipeline (Standard 2.0 workflow)

The creative process splits into two stages with a human decision point between them:

**Stage 1 — Territory generation.** Creative 1 generates `n` creative territories (default 3, configurable 1–10) from the creative brief. Each territory is a tight artifact: title, core idea (1–2 sentences), and a brief rationale connecting it to the brief. No execution details, no campaign specifics — just the central creative thought.

**Stage 2 — Campaign development.** After the user selects a territory, Creative 2 develops it into a full campaign concept with deliverables, channel recommendations, and execution direction. The output is a structured `CampaignConcept` model (title, core idea, deliverables list, rationale) enforced via `with_structured_output()`, giving the grader and synthesis clean typed input.

The two stages use different agents with different prompts. Creative 1 is optimised for divergent thinking (generate many distinct directions). Creative 2 is optimised for convergent development (deepen one direction into a viable campaign).

### 2. Human-in-the-loop territory selection via LangGraph interrupt

After Creative 1 generates territories, the graph pauses using LangGraph's `interrupt()` mechanism. The user sees all territories as modular cards, selects one to develop, or reruns Creative 1 (with optional single-sentence rejection context to steer the next batch).

This requires a **checkpointer**. Phase 1 uses `MemorySaver` (in-memory, zero dependencies, state lost on process restart). The checkpointer interface is standard LangGraph, so upgrading to a persistent backend (SQLite, Postgres) later is a config change.

The interrupt point is the first human-in-the-loop feature in the project. It establishes the pattern for future interrupt points (e.g. campaign approval before asset generation).

### 3. Three-role Creative Director split

The current single CD splits into three roles with distinct responsibilities, temperatures, and schemas:

**CD Grader** (`agents/cd_grader.py`) — Scoring only. Temperature hardcoded to 0. No philosophy or provenance injection. Lean output schema: score (0–100) + brief rationale. Fires after every Creative 2 iteration. Its job is *measurement* — consistent, repeatable, unbiased. The score drives the approval gate routing, same numeric comparison pattern as v1.

**CD Feedback** (`agents/cd_feedback.py`) — Revision direction only. Creative temperature (configurable via sidebar slider). Philosophy and provenance injected. Fires only when a campaign is rejected (score below threshold, iterations remaining). Its job is *coaching* — actionable direction for Creative 2's next iteration. Does not score.

**CD Synthesis** (`agents/cd_synthesis.py`) — Final editorial judgement. Creative temperature (configurable). Philosophy and provenance injected. Fires once at the end. Receives the approved (or best-of) campaign concept, evaluates it holistically, and presents the recommendation to the user. Built to handle N concepts and select the best — in this phase it receives 1, but the schema and prompt support comparison for the future parallel variant (see Non-goals). Output is a structured `CDSynthesis` model: selected title, recommendation narrative, per-concept score summary, and optional comparison notes (None when N=1).

The existing `agents/creative_director.py` is untouched. Standard 1.0 continues to use it.

### 4. Iteration loop structure (Standard 2.0)

```
Creative 2 → CD Grader (score + rationale, temp=0)
  → score ≥ threshold → CD Synthesis → END
  → score < threshold, iterations remain → CD Feedback → Creative 2 (loop)
  → score < threshold, max iterations → CD Synthesis (best-of) → END
```

Same two-gate pattern as ADR 0006 (approval check → iteration check), same `approval_threshold` and `max_iterations` config knobs, same best-of fallback on exhaustion. The difference is that scoring and feedback are now separate LLM calls at different temperatures.

### 5. Provenance and taste as new prompt injection categories

Two new prompt injection categories following the ADR 0010 filesystem-backed pattern:

**Provenance** — details about the creative practitioner's background and upbringing that shape their worldview. Stored as `.txt` files in `prompts/provenance/`, loaded via `load_provenance()`. Enum: `Provenance` (3 initial presets + `NEUTRAL`). Neutral skips injection entirely, same pattern as philosophy.

**Taste** — details about creative passions, dislikes, influences, and aesthetic preferences. Stored as `.txt` files in `prompts/taste/`, loaded via `load_taste()`. Enum: `Taste` (3 initial presets + `NEUTRAL`). Same skip pattern.

Sidebar scoping: one provenance/taste selector per creative role (Creative 1, Creative 2, CD — where "CD" covers CD Feedback and CD Synthesis). The CD Grader is always neutral on both — no injection.

### 6. Per-agent temperature control

`get_llm()` gains an optional `temperature: float | None` parameter. When `None`, the provider's default is used. When set, it's passed through to the underlying chat model constructor.

Sidebar exposes temperature sliders for: Creative 1, Creative 2, CD Feedback, CD Synthesis. Default: 0.7 for all four. CD Grader is hardcoded to 0 — no slider.

Temperature values are stored on `AgencyState` as per-agent fields so they flow through the graph and are recorded in history for reproducibility.

### 7. Territory and campaign concept as modular data models

Territories are `list[Territory]` on `AgencyState`, where `Territory` is:

```python
class Territory(BaseModel):
    title: str
    core_idea: str
    why_it_works: str
```

Campaign output is a structured `CampaignConcept` on `AgencyState`:

```python
class CampaignDeliverable(BaseModel):
    name: str
    explanation: str

class CampaignConcept(BaseModel):
    title: str
    core_idea: str
    deliverables: list[CampaignDeliverable]
    why_it_works: str
```

Territory count is controlled by `num_territories: int = Field(default=3, ge=1, le=10)` on `AgencyState`. The creative standalone page exposes this as a numeric input. The workflow page uses the default.

Territories are independent modular blocks. Each is a self-contained object that can be passed to Creative 2 (or, in future, to parallel Creative 2 instances). The user's selection is tracked as `selected_territory: Territory | None` on state.

### 8. Tab structure

**Workflow page:** Two tabs. "Standard 2.0" (default, left) runs the new pipeline. "Standard 1.0" (right) runs the existing v1 pipeline unchanged.

**Creative page:** Two tabs. "c1_territory" (default, left) uses Creative 1 for territory generation. "c0_original" (right) preserves the current creative agent functionality.

### 9. New graph definition

The v2 workflow lives in `graph/workflow_v2.py`. The v1 graph in `graph/workflow.py` is untouched. Both are importable independently. The workflow page imports whichever graph the active tab requires.

All v1 infrastructure carries forward: `_safe_node()` wrapping, `format_node_error()`, error guards on routing functions, `FAILED` contract, `WorkflowStatus` enum. New v2-specific statuses may be added to the enum (e.g. `TERRITORY_SELECTION_PENDING`).

## Consequences

- **Positive:** Territory generation is tighter and more focused. 1–2 sentence core ideas force the LLM to crystallise the creative thought before worrying about execution. The user sees the raw ideas and picks the strongest.
- **Positive:** Human-in-the-loop at the most valuable decision point. Creative professionals choose which territory to back — the system develops their choice, not its own.
- **Positive:** Scoring is separated from feedback, each at the appropriate temperature. Grader scores are more consistent (temp=0), feedback is more creative (configurable temp). The routing decision is based on objective measurement, not a score influenced by creative latitude.
- **Positive:** Provenance and taste add genuinely novel creative dimensions. The same brief processed through different provenance profiles produces materially different creative directions — this is the tool's differentiator.
- **Positive:** Modular territory blocks and a synthesis model built for N concepts mean the parallel v2 variant (3× Creative 2) requires no state model rearchitect — just graph changes.
- **Positive:** Standard 1.0 is preserved. No risk to the existing deployed workflow. Users can compare v1 and v2 output on the same brief.
- **Negative:** Cost per run increases. Worst case for v2: 1 strategist + 1 Creative 1 + (3 iterations × (1 Creative 2 + 1 Grader + 1 CD Feedback)) + 1 CD Synthesis = **12 LLM calls** (vs 11 for v1 worst case). Typical case is lower — most campaigns approve in 1–2 iterations. The grader at temp=0 can use a smaller/cheaper model if cost pressure requires it.
- **Negative:** Interrupt/resume adds complexity. The checkpointer, the interrupt point, and the resume-with-user-input pattern are all new to the project. `MemorySaver` keeps the infrastructure minimal but the graph logic is still more complex than v1.
- **Negative:** Five new agent files (Creative 1, Creative 2, CD Grader, CD Feedback, CD Synthesis) plus new prompt files for provenance and taste. The codebase grows significantly. Each agent follows existing conventions, so the pattern is established, but the surface area for bugs increases.
- **Negative:** Sidebar complexity increases substantially. Per-role provenance/taste selectors (3 roles), per-agent temperature sliders (4 agents), plus existing philosophy selectors. Will require careful UI organisation — likely collapsible sections or an "advanced" toggle.
- **Neutral:** The existing `creative_director.py` is not refactored or deprecated. It continues to serve Standard 1.0. If Standard 1.0 is eventually removed, it can be deleted cleanly.

## Non-goals

- **Parallel Creative 2 (3× campaign development).** The state model and CD Synthesis are built to support N concepts, but the graph only develops one territory in this phase. Parallel branches are a future workflow variant.
- **Creative 3 (asset generation).** Not part of the current flow. Will be a separate phase when the production module is developed.
- **Persistent checkpointer.** `MemorySaver` is sufficient for synchronous territory selection within a single session. Persistent checkpointing (SQLite/Postgres) is deferred until long-running or cross-session workflows are needed.
- **Grader rubric differentiation per stage.** The simplified workflow has only one grading stage (after Creative 2). When the parallel v2 introduces grading after Creative 1 as well, stage-specific rubrics will be needed — the grader prompt is already parameterisable for this, but the rubric content is deferred.