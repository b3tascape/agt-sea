"""
agt_sea v001 — Data Models

Defines the shared state that flows through the LangGraph agent graph,
plus supporting models for structured evaluation and iteration history.
"""

from __future__ import annotations

from datetime import datetime
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
    evaluation lens. Each value acts as a key that maps to a detailed
    system prompt defining the CD's creative perspective and standards.
    """
    BOLD_AND_DISRUPTIVE = "bold_and_disruptive"
    MINIMAL_AND_REFINED = "minimal_and_refined"
    EMOTIONALLY_DRIVEN = "emotionally_driven"
    DATA_LED = "data_led"
    CULTURALLY_PROVOCATIVE = "culturally_provocative"


# ---------------------------------------------------------------------------
# Supporting models
# ---------------------------------------------------------------------------

class CDEvaluation(BaseModel):
    """Structured evaluation from the Creative Director."""
    score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Quality score out of 100. Threshold for approval is 80.",
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
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
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
        ...,
        description="The raw client brief as supplied.",
    )
    creative_philosophy: CreativePhilosophy = Field(
        default=CreativePhilosophy.BOLD_AND_DISRUPTIVE,
        description="The creative lens the CD uses to evaluate and direct work.",
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
        default=5,
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
