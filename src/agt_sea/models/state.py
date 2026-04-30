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
    """Identifies which agent produced an output.

    Standard 1.0 and Standard 2.0 share this namespace.
    """
    STRATEGIST_ST1 = "strategist_st1"
    CREATIVE_ST1 = "creative_st1"
    CREATIVE_DIRECTOR_ST1 = "creative_director_st1"
    STRATEGIST_ST2 = "strategist_st2"
    CREATIVE_A_ST2 = "creative_a_st2"          # [2.0] Territory generation
    CREATIVE_B_ST2 = "creative_b_st2"          # [2.0] Campaign development
    CD_GRADER_ST2 = "cd_grader_st2"            # [2.0] Scoring-only evaluation
    CD_FEEDBACK_ST2 = "cd_feedback_st2"        # [2.0] Revision direction
    CD_SYNTHESIS_ST2 = "cd_synthesis_st2"      # [2.0] Final editorial judgement


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
    into Creative A, Creative B, CD Feedback, and CD Synthesis prompts. Each
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
    preferences) injected into Creative A, Creative B, CD Feedback, and CD
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
    A single creative territory produced by Creative A. Tight artifact:
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
    Structured output of Creative B — a selected territory developed into a
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
    the model carries forward into the future parallel Creative B variant;
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
    # Per-agent philosophy lenses. Standard 1.0 and Standard 2.0 each get
    # their own set so the two pipelines can be steered independently. CD
    # Grader (st2) is omitted on purpose — neutral by contract.
    strategist_st1_strategic_philosophy: StrategicPhilosophy = Field(
        default=StrategicPhilosophy.NEUTRAL,
        description="Strategic lens for the Standard 1.0 Strategist.",
    )
    creative_st1_creative_philosophy: CreativePhilosophy = Field(
        default=CreativePhilosophy.NEUTRAL,
        description="Creative lens for the Standard 1.0 Creative agent.",
    )
    creative_director_st1_creative_philosophy: CreativePhilosophy = Field(
        default=CreativePhilosophy.NEUTRAL,
        description="Creative lens for the Standard 1.0 Creative Director.",
    )
    strategist_st2_strategic_philosophy: StrategicPhilosophy = Field(
        default=StrategicPhilosophy.NEUTRAL,
        description="Strategic lens for the Standard 2.0 Strategist.",
    )
    creative_a_st2_creative_philosophy: CreativePhilosophy = Field(
        default=CreativePhilosophy.NEUTRAL,
        description="Creative lens for Creative A (territory generation, Standard 2.0).",
    )
    creative_b_st2_creative_philosophy: CreativePhilosophy = Field(
        default=CreativePhilosophy.NEUTRAL,
        description="Creative lens for Creative B (campaign development, Standard 2.0).",
    )
    creative_director_st2_creative_philosophy: CreativePhilosophy = Field(
        default=CreativePhilosophy.NEUTRAL,
        description=(
            "Creative lens shared by CD Feedback and CD Synthesis (Standard "
            "2.0). CD Grader is neutral by contract and has no philosophy."
        ),
    )
    # [2.0] Per-role provenance / taste lenses. CD pair is shared by CD Feedback
    # and CD Synthesis; CD Grader is always neutral by contract.
    creative_a_st2_provenance: Provenance = Field(
        default=Provenance.NEUTRAL,
        description="Provenance lens for Creative A (territory generation).",
    )
    creative_a_st2_taste: Taste = Field(
        default=Taste.NEUTRAL,
        description="Taste lens for Creative A (territory generation).",
    )
    creative_b_st2_provenance: Provenance = Field(
        default=Provenance.NEUTRAL,
        description="Provenance lens for Creative B (campaign development).",
    )
    creative_b_st2_taste: Taste = Field(
        default=Taste.NEUTRAL,
        description="Taste lens for Creative B (campaign development).",
    )
    creative_director_st2_provenance: Provenance = Field(
        default=Provenance.NEUTRAL,
        description="Provenance lens shared by CD Feedback and CD Synthesis.",
    )
    creative_director_st2_taste: Taste = Field(
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
        description="Creative A output. Length == `num_territories` on success.",
    )
    num_territories: int = Field(
        default=3,
        ge=1,
        le=12,
        description="How many territories Creative A should generate.",
    )
    selected_territory: Territory | None = Field(
        default=None,
        description="Territory chosen by the user at the interrupt; input to Creative B.",
    )
    territory_rejection_context: str | None = Field(
        default=None,
        description=(
            "Optional user feedback supplied when rerunning Creative A "
            "instead of selecting a territory. Steers the next batch."
        ),
    )
    # [2.0] Campaign stage outputs.
    campaign_concept: CampaignConcept | None = Field(
        default=None,
        description="Creative B output — structured campaign with deliverables.",
    )
    grader_evaluation: GraderEvaluation | None = Field(
        default=None,
        description="Latest CD Grader score + rationale for the current campaign.",
    )
    cd_feedback_direction: str | None = Field(
        default=None,
        description=(
            "Qualitative revision direction produced by CD Feedback on rejected "
            "campaigns. Read by Creative B on its revision path."
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
    creative_a_st2_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature passed to `get_llm()` when invoking Creative A.",
    )
    creative_b_st2_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature passed to `get_llm()` when invoking Creative B.",
    )
    cd_feedback_st2_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature for the CD Feedback agent (qualitative revision direction).",
    )
    cd_synthesis_st2_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature for the CD Synthesis agent (final editorial judgement).",
    )
    cd_grader_st2_temperature: float = Field(
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
