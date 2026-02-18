"""
agt_sea — Configuration

Centralised settings with sensible defaults. Environment variables
(via .env) override defaults where provided.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from agt_sea.models.state import LLMProvider

load_dotenv()


# ---------------------------------------------------------------------------
# LLM Provider
# ---------------------------------------------------------------------------

def get_llm_provider() -> LLMProvider:
    """Return the active LLM provider, defaulting to Anthropic."""
    
    raw = (os.getenv("LLM_PROVIDER") or "anthropic").lower() #sm: previous: raw = os.getenv("LLM_PROVIDER", "anthropic").lower()
    try:
        return LLMProvider(raw)
    except ValueError:
        valid = ", ".join(p.value for p in LLMProvider)
        raise ValueError(
            f"Invalid LLM_PROVIDER '{raw}'. Must be one of: {valid}"
        )


# ---------------------------------------------------------------------------
# Model names — one per provider
# ---------------------------------------------------------------------------

DEFAULT_MODELS: dict[LLMProvider, str] = {
    LLMProvider.ANTHROPIC: "claude-sonnet-4-20250514",
    LLMProvider.GOOGLE: "gemini-2.0-flash",
    LLMProvider.OPENAI: "gpt-4o",
}


def get_model_name(provider: LLMProvider | None = None) -> str:
    """Return the model name for the given provider.

    Can be overridden via MODEL_NAME env var.
    """
    provider = provider or get_llm_provider()
    return os.getenv("MODEL_NAME", DEFAULT_MODELS[provider])


# ---------------------------------------------------------------------------
# Workflow defaults
# ---------------------------------------------------------------------------

MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "5"))
APPROVAL_THRESHOLD: float = float(os.getenv("APPROVAL_THRESHOLD", "80.0"))
