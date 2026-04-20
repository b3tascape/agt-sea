"""
agt_sea — Data Models

Defines the shared state that flows through the LangGraph agent graph,
plus supporting models for structured evaluation and iteration history.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class WorkflowStatus(str, Enum):
    """Current status of the overall workflow."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    APPROVED = "approved"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"
    FAILED = "failed"


class AgentRole(str, Enum):
    """Identifies which agent produced an output."""
    STRATEGIST = "strategist"
    CREATIVE = "creative"
    CREATIVE_DIRECTOR = "creative_director"


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENAI = "openai"


class CreativePhilosophy(str, Enum):
    """
    Pre-defined creative philosophies that shape the Creative Director's
    evaluation lens. Each value (except NEUTRAL) maps to a detailed
    system prompt defining the CD's creative perspective and standards.
    NEUTRAL bypasses philosophy injection entirely.
    """
    NEUTRAL = "neutral"
    BOLD_AND_DISRUPTIVE = "bold_and_disruptive"
    MINIMAL_AND_REFINED = "minimal_and_refined"
    EMOTIONALLY_DRIVEN = "emotionally_driven"
    DATA_LED = "data_led"
    CULTURALLY_PROVOCATIVE = "culturally_provocative"


class StrategicPhilosophy(str, Enum):
    """
    Pre-defined strategic philosophies that shape the Strategist's
    approach and lens. Each value (except NEUTRAL) maps to a detailed
    prompt file defining the strategic perspective.
    """
    NEUTRAL = "neutral"
    CHALLENGER = "challenger"
    HUMAN_FIRST = "human_first"
    CULTURAL_STRATEGY = "cultural_strategy"
    BRAND_WORLD = "brand_world"
    COMMERCIAL_PRAGMATIST = "commercial_pragmatist"


class Provenance(str, Enum):
    """
    Creative practitioner background presets (upbringing, worldview) injected
    into Creative 1, Creative 2, CD Feedback, and CD Synthesis prompts. Each
    value (except NEUTRAL) maps to a prompt file in `prompts/provenance/`.
    NEUTRAL bypasses injection entirely.

    Prompt content is authored in Phase B of the Standard 2.0 workplan.
    """
    NEUTRAL = "neutral"
    NORTHERN_WORKING_CLASS = "northern_working_class"
    METROPOLITAN_ACADEMIC = "metropolitan_academic"
    DIY_SUBCULTURE = "diy_subculture"


class Taste(str, Enum):
    """
    Creative taste presets (passions, dislikes, influences, aesthetic
    preferences) injected into Creative 1, Creative 2, CD Feedback, and CD
    Synthesis prompts. Each value (except NEUTRAL) maps to a prompt file in
    `prompts/taste/`. NEUTRAL bypasses injection entirely.

    Prompt content is authored in Phase B of the Standard 2.0 workplan.
    """
    NEUTRAL = "neutral"
    UNDERGROUND_REFERENTIAL = "underground_referential"
    AVANT_GARDE = "avant_garde"
    POP_MAXIMALIST = "pop_maximalist"
    CRAFT_TRADITIONALIST = "craft_traditionalist"


# ---------------------------------------------------------------------------
# Supporting models
# ---------------------------------------------------------------------------

class CDEvaluation(BaseModel):
    """Structured evaluation from the Creative Director (Standard 1.0)."""
    score: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Quality score out of 100. The approval threshold is "
            "configurable per run via AgencyState.approval_threshold "
            "(default 80.0)."
        ),
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="What works well in the creative output.",
    )
    weaknesses: list[str] = Field(
        default_factory=list,
        description="What needs improvement.",
    )
    direction: str = Field(
        ...,
        description="Actionable feedback for the next creative iteration.",
    )


class AgentOutput(BaseModel):
    """A single output produced by an agent, stored in iteration history."""
    agent: AgentRole
    provider: LLMProvider
    model: str = Field(
        ...,
        description="The model name used for this output.",
    )
    iteration: int = Field(
        ...,
        description="The iteration number when this output was produced.",
    )
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    evaluation: CDEvaluation | None = Field(
        default=None,
        description="Present only when agent is creative_director.",
    )


# [2.0] Creative artifacts produced by the multi-stage pipeline (see ADR 0014).

class Territory(BaseModel):
    """
    A single creative territory produced by Creative 1. Tight artifact:
    central creative thought only — no execution details.
    """
    title: str = Field(
        ...,
        description="Short, evocative name for the territory.",
    )
    core_idea: str = Field(
        ...,
        description="The central creative thought in 1–2 sentences.",
    )
    why_it_works: str = Field(
        ...,
        description="Brief rationale connecting the idea back to the brief.",
    )


class CampaignDeliverable(BaseModel):
    """A single deliverable within a campaign concept (e.g. a channel activation)."""
    name: str = Field(
        ...,
        description="Deliverable name (e.g. 'Launch film', 'OOH series').",
    )
    explanation: str = Field(
        ...,
        description="How the deliverable executes the core idea.",
    )


class CampaignConcept(BaseModel):
    """
    Structured output of Creative 2 — a selected territory developed into a
    full campaign with deliverables. Enforced via `with_structured_output()`.
    """
    title: str = Field(
        ...,
        description="Campaign title.",
    )
    core_idea: str = Field(
        ...,
        description="The central creative thought carried from the selected territory.",
    )
    deliverables: list[CampaignDeliverable] = Field(
        default_factory=list,
        description="Concrete executions across channels/formats.",
    )
    why_it_works: str = Field(
        ...,
        description="Rationale for why this campaign delivers on the brief.",
    )


class GraderEvaluation(BaseModel):
    """
    Structured output of the CD Grader. Scoring only — no qualitative
    feedback, no philosophy injection. Temperature is hardcoded to 0 at the
    agent level for repeatable scoring.
    """
    score: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Quality score out of 100. Drives the approval-gate routing in "
            "the Standard 2.0 graph (compared against `approval_threshold`)."
        ),
    )
    rationale: str = Field(
        ...,
        description="Brief justification for the score.",
    )


class ConceptScoreSummary(BaseModel):
    """
    Per-concept summary inside `CDSynthesis`. Built to support N concepts so
    the model carries forward into the future parallel Creative 2 variant;
    the current graph passes a single-element list.
    """
    title: str = Field(
        ...,
        description="Campaign concept title being summarised.",
    )
    score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Grader score for this concept.",
    )
    assessment: str = Field(
        ...,
        description="CD's short editorial read on this concept.",
    )


class CDSynthesis(BaseModel):
    """
    Structured output of CD Synthesis — final editorial judgement delivered
    to the user. Schema supports N concepts (see `ConceptScoreSummary`); the
    simplified Standard 2.0 graph passes one.
    """
    selected_title: str = Field(
        ...,
        description="Title of the concept the CD recommends.",
    )
    recommendation: str = Field(
        ...,
        description="Narrative recommendation presented to the user.",
    )
    score_summary: list[ConceptScoreSummary] = Field(
        default_factory=list,
        description="Per-concept summaries. Single element in the simplified v2 graph.",
    )
    comparison_notes: str | None = Field(
        default=None,
        description="Cross-concept commentary. None when only one concept is evaluated.",
    )


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------

class AgencyState(BaseModel):
    """
    Shared state object passed through the LangGraph agent graph.

    This is the single source of truth at every node. Each agent reads
    what it needs and appends its output to the history.
    """

    # --- Input ---
    client_brief: str = Field(
        default="",
        description="The raw client brief as supplied.",
    )
    strategic_philosophy: StrategicPhilosophy = Field(
        default=StrategicPhilosophy.NEUTRAL,
        description="The strategic lens the Strategist uses when writing the brief.",
    )
    creative_philosophy: CreativePhilosophy = Field(
        default=CreativePhilosophy.NEUTRAL,
        description="The creative lens the Creative agent uses when generating ideas.",
    )
    cd_philosophy: CreativePhilosophy = Field(
        default=CreativePhilosophy.NEUTRAL,
        description="The creative lens the Creative Director uses to evaluate and direct work.",
    )
    # [2.0] Per-role provenance / taste lenses. CD pair is shared by CD Feedback
    # and CD Synthesis; CD Grader is always neutral by contract.
    creative1_provenance: Provenance = Field(
        default=Provenance.NEUTRAL,
        description="Provenance lens for Creative 1 (territory generation).",
    )
    creative1_taste: Taste = Field(
        default=Taste.NEUTRAL,
        description="Taste lens for Creative 1 (territory generation).",
    )
    creative2_provenance: Provenance = Field(
        default=Provenance.NEUTRAL,
        description="Provenance lens for Creative 2 (campaign development).",
    )
    creative2_taste: Taste = Field(
        default=Taste.NEUTRAL,
        description="Taste lens for Creative 2 (campaign development).",
    )
    cd_provenance: Provenance = Field(
        default=Provenance.NEUTRAL,
        description="Provenance lens shared by CD Feedback and CD Synthesis.",
    )
    cd_taste: Taste = Field(
        default=Taste.NEUTRAL,
        description="Taste lens shared by CD Feedback and CD Synthesis.",
    )

    # --- LLM overrides (optional — fall back to config defaults when None) ---
    llm_provider: LLMProvider | None = Field(
        default=None,
        description=(
            "Optional provider override. When None, agents fall back to the "
            "provider from config (env var / st.secrets / default)."
        ),
    )
    llm_model: str | None = Field(
        default=None,
        description=(
            "Optional model-name override. When None, agents fall back to "
            "get_model_name(provider) from config."
        ),
    )

    # --- Agent outputs (latest for quick access) ---
    creative_brief: str | None = Field(
        default=None,
        description="Latest creative brief produced by the strategist.",
    )
    creative_concept: str | None = Field(
        default=None,
        description="Latest creative concept produced by the creative agent.",
    )
    cd_evaluation: CDEvaluation | None = Field(
        default=None,
        description="Latest evaluation from the creative director.",
    )
    # [2.0] Territory stage outputs + user input at the interrupt.
    territories: list[Territory] = Field(
        default_factory=list,
        description="Creative 1 output. Length == `num_territories` on success.",
    )
    num_territories: int = Field(
        default=3,
        ge=1,
        le=10,
        description="How many territories Creative 1 should generate.",
    )
    selected_territory: Territory | None = Field(
        default=None,
        description="Territory chosen by the user at the interrupt; input to Creative 2.",
    )
    territory_rejection_context: str | None = Field(
        default=None,
        description=(
            "Optional user feedback supplied when rerunning Creative 1 "
            "instead of selecting a territory. Steers the next batch."
        ),
    )
    # [2.0] Campaign stage outputs.
    campaign_concept: CampaignConcept | None = Field(
        default=None,
        description="Creative 2 output — structured campaign with deliverables.",
    )
    grader_evaluation: GraderEvaluation | None = Field(
        default=None,
        description="Latest CD Grader score + rationale for the current campaign.",
    )
    cd_feedback_direction: str | None = Field(
        default=None,
        description=(
            "Qualitative revision direction produced by CD Feedback on rejected "
            "campaigns. Read by Creative 2 on its revision path."
        ),
    )
    cd_synthesis: CDSynthesis | None = Field(
        default=None,
        description="Final editorial judgement emitted by CD Synthesis before END.",
    )

    # --- Iteration tracking ---
    iteration: int = Field(
        default=0,
        description="Current iteration count for the creative loop.",
    )
    max_iterations: int = Field(
        default=3,
        description="Maximum allowed iterations before forced exit.",
    )
    approval_threshold: float = Field(
        default=80.0,
        description="Minimum cd_score required for approval.",
    )
    # [2.0] Per-agent temperature. Grader is hardcoded to 0.0 for repeatable
    # scoring and is not sidebar-exposed; kept on state for traceability.
    creative1_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature passed to `get_llm()` when invoking Creative 1.",
    )
    creative2_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature passed to `get_llm()` when invoking Creative 2.",
    )
    cd_feedback_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature for the CD Feedback agent (qualitative revision direction).",
    )
    cd_synthesis_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature for the CD Synthesis agent (final editorial judgement).",
    )
    grader_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Temperature for the CD Grader — hardcoded default for repeatable scoring.",
    )

    # --- History ---
    history: list[AgentOutput] = Field(
        default_factory=list,
        description="Ordered log of every agent output across all iterations.",
    )

    # --- Workflow ---
    status: WorkflowStatus = Field(
        default=WorkflowStatus.PENDING,
        description="Current status of the workflow.",
    )
    error: str | None = Field(
        default=None,
        description=(
            "Populated when a node fails. Contract between the graph and "
            "the frontend for FAILED runs — the frontend reads this after "
            "rehydration to render an error state instead of agent output."
        ),
    )
