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
# Bridge st.secrets -> os.environ for Streamlit Cloud
# ---------------------------------------------------------------------------
# LangChain providers read API keys directly from os.environ
# (e.g. ANTHROPIC_API_KEY). On Streamlit Cloud, secrets live in
# st.secrets instead, so we inject them into the environment.

_API_KEY_NAMES = [
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
]

# Streamlit may not be importable in every context (tests, scripts),
# and st.secrets raises FileNotFoundError when no secrets file is present.
try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for key in _API_KEY_NAMES:
            if key not in os.environ and key in st.secrets:
                os.environ[key] = st.secrets[key]
except (ImportError, AttributeError, FileNotFoundError):
    pass


# ---------------------------------------------------------------------------
# Secret / env var helper -- .env first, then st.secrets fallback
# ---------------------------------------------------------------------------

def _get_secret(key: str, default: str | None = None) -> str | None:
    """Read a value from environment variables, falling back to
    Streamlit secrets when running on Streamlit Cloud.

    Priority: os.environ (.env) -> st.secrets -> default
    """
    value = os.environ.get(key)
    if value:
        return value

    # Streamlit Cloud stores secrets in st.secrets. Same caveats as the
    # bridge above — streamlit may not be importable, and st.secrets
    # raises FileNotFoundError when no secrets file is present.
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except (ImportError, AttributeError, FileNotFoundError):
        pass

    return default


# ---------------------------------------------------------------------------
# LLM Provider
# ---------------------------------------------------------------------------

def get_llm_provider() -> LLMProvider:
    """Return the active LLM provider, defaulting to Anthropic."""
    raw = (_get_secret("LLM_PROVIDER") or "anthropic").lower()
    try:
        return LLMProvider(raw)
    except ValueError:
        valid = ", ".join(p.value for p in LLMProvider)
        raise ValueError(
            f"Invalid LLM_PROVIDER '{raw}'. Must be one of: {valid}"
        )


# ---------------------------------------------------------------------------
# Model names -- one per provider, with per-provider secret overrides
# ---------------------------------------------------------------------------

DEFAULT_MODELS: dict[LLMProvider, str] = {
    LLMProvider.ANTHROPIC: "claude-sonnet-4-6",
    LLMProvider.GOOGLE: "gemini-3-flash-preview",
    LLMProvider.OPENAI: "gpt-5.4-mini",
}

# Full list of models selectable in the frontend sidebar, per provider.
# The default from DEFAULT_MODELS (or a per-provider secret override) must
# appear in this list for the sidebar default selection to line up.
AVAILABLE_MODELS: dict[LLMProvider, list[str]] = {
    LLMProvider.ANTHROPIC: [
        "claude-haiku-4-5-20251001",
        "claude-sonnet-4-6",
        "claude-opus-4-6",
    ],
    LLMProvider.GOOGLE: [
        "gemini-3.1-flash-lite-preview",
        "gemini-3-flash-preview",
        "gemini-3.1-pro-preview",
    ],
    LLMProvider.OPENAI: [
        "gpt-5.4-nano",
        "gpt-5.4-mini",
        "gpt-5.4",
    ],
}

_PROVIDER_MODEL_KEYS: dict[LLMProvider, str] = {
    LLMProvider.ANTHROPIC: "ANTHROPIC_MODEL",
    LLMProvider.GOOGLE: "GOOGLE_MODEL",
    LLMProvider.OPENAI: "OPENAI_MODEL",
}


def get_model_name(provider: LLMProvider | None = None) -> str:
    """Return the model name for the given provider.

    Checks for a provider-specific secret first (e.g. ANTHROPIC_MODEL),
    then falls back to DEFAULT_MODELS. This allows Streamlit Cloud to
    set cost-controlled models per provider independently.
    """
    provider = provider or get_llm_provider()
    secret_key = _PROVIDER_MODEL_KEYS[provider]
    return _get_secret(secret_key) or DEFAULT_MODELS[provider]


# ---------------------------------------------------------------------------
# Workflow defaults
# ---------------------------------------------------------------------------

MAX_ITERATIONS: int = int(_get_secret("MAX_ITERATIONS") or "3")
APPROVAL_THRESHOLD: float = float(_get_secret("APPROVAL_THRESHOLD") or "80.0")


# ---------------------------------------------------------------------------
# Transport-level retry policy
# ---------------------------------------------------------------------------
# Number of attempts (including the first) made by wrap_with_transport_retry()
# in llm/provider.py when an LLM call raises a transient transport error.
# The retry allowlist is per-provider and defined in provider.py; this knob
# just bounds how many attempts are made before the error propagates.

LLM_MAX_RETRIES: int = int(_get_secret("LLM_MAX_RETRIES") or "3")
