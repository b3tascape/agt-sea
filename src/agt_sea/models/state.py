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


# ---------------------------------------------------------------------------
# Supporting models
# ---------------------------------------------------------------------------

class CDEvaluation(BaseModel):
    """Structured evaluation from the Creative Director."""
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
