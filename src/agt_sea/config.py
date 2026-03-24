"""
agt_sea — Configuration

Centralised settings with sensible defaults. Environment variables
(via .env) override defaults where provided. When deployed to
Streamlit Cloud, secrets are read from st.secrets as a fallback.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from agt_sea.models.state import LLMProvider

load_dotenv()


# ---------------------------------------------------------------------------
# Bridge st.secrets → os.environ for Streamlit Cloud
# ---------------------------------------------------------------------------
# LangChain providers read API keys directly from os.environ
# (e.g. ANTHROPIC_API_KEY). On Streamlit Cloud, secrets live in
# st.secrets instead, so we inject them into the environment.

_API_KEY_NAMES = [
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
]

try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for key in _API_KEY_NAMES:
            if key not in os.environ and key in st.secrets:
                os.environ[key] = st.secrets[key]
except Exception:
    pass


# ---------------------------------------------------------------------------
# Secret / env var helper — .env first, then st.secrets fallback
# ---------------------------------------------------------------------------

def _get_secret(key: str, default: str | None = None) -> str | None:
    """Read a value from environment variables, falling back to
    Streamlit secrets when running on Streamlit Cloud.

    Priority: os.environ (.env) → st.secrets → default
    """
    value = os.environ.get(key)
    if value:
        return value

    # Streamlit Cloud stores secrets in st.secrets
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass

    return default


# ---------------------------------------------------------------------------
# LLM Provider
# ---------------------------------------------------------------------------

def get_llm_provider() -> LLMProvider:
    """Return the active LLM provider, defaulting to Anthropic."""
    
    # [NO STREAMLIT APPROACH 1/4] raw = (os.getenv("LLM_PROVIDER") or "anthropic").lower() #sm: previous: raw = os.getenv("LLM_PROVIDER", "anthropic").lower()
    raw = (_get_secret("LLM_PROVIDER") or "anthropic").lower()
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
    LLMProvider.ANTHROPIC: "claude-sonnet-4-6", # "claude-haiku-4-5-20251001" | "claude-sonnet-4-6" | "claude-opus-4-6" | "claude-sonnet-4-5-20250929" | "claude-sonnet-4-20250514"
    LLMProvider.GOOGLE: "gemini-2.5-flash", # "gemini-3-flash-preview" | gemini-3-pro-preview" | "gemini-2.5-flash-lite" | "gemini-2.5-flash" | "gemini-2.5-pro" | "gemini-2.0-flash"
    LLMProvider.OPENAI: "gpt-4o", # 
}


def get_model_name(provider: LLMProvider | None = None) -> str:
    """Return the model name for the given provider.

    Can be overridden via MODEL_NAME env var / secret.
    """
    provider = provider or get_llm_provider()
    # [NO STREAMLIT APPROACH 2/4] return (os.getenv("MODEL_NAME") or DEFAULT_MODELS[provider]) #sm return os.getenv("MODEL_NAME", DEFAULT_MODELS[provider])
    return _get_secret("MODEL_NAME") or DEFAULT_MODELS[provider]


# ---------------------------------------------------------------------------
# Workflow defaults
# ---------------------------------------------------------------------------

# [NO STREAMLIT APPROACH 3/4] MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS") or "5") #sm MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "5"))
# [NO STREAMLIT APPROACH 4/4] APPROVAL_THRESHOLD: float = float(os.getenv("APPROVAL_THRESHOLD") or "80.0") #sm APPROVAL_THRESHOLD: float = float(os.getenv("APPROVAL_THRESHOLD", "80.0"))
MAX_ITERATIONS: int = int(_get_secret("MAX_ITERATIONS") or "5")
APPROVAL_THRESHOLD: float = float(_get_secret("APPROVAL_THRESHOLD") or "85.0")

