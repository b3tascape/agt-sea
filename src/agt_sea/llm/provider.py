"""
agt_sea — LLM Provider Abstraction

A single entry point that returns a LangChain chat model for whichever
provider is configured. All agents import from here rather than
instantiating models directly.

This module also owns the transport-level retry policy: wrap any runnable
with wrap_with_transport_retry() to get exponential backoff on transient
network / rate-limit / 5xx errors, using a per-provider exception allowlist.
Callers that compose BaseChatModel-only methods (e.g.
.with_structured_output()) should request an unwrapped model via
get_llm(with_retry=False), apply those methods, then wrap the result
with wrap_with_transport_retry() manually. See ADR 0012 (pending).
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable

from agt_sea.config import LLM_MAX_RETRIES, get_llm_provider, get_model_name
from agt_sea.models.state import LLMProvider


# ---------------------------------------------------------------------------
# Transport retry — per-provider exception allowlist
# ---------------------------------------------------------------------------
#
# Retry policy (decided in Phase 6.1):
#
#   RETRY these (allowlist — transient transport errors only):
#     - network / connection failures
#     - timeouts
#     - HTTP 429 rate-limit errors, where the provider SDK raises a
#       distinct class we can match on
#     - HTTP 5xx server errors (including Anthropic 529 "overloaded",
#       which surfaces as InternalServerError)
#
#   DO NOT retry (must be excluded — deliberate, not oversight):
#     - auth errors (401 / 403)
#     - 4xx client errors (bad request, not found, unprocessable, etc.)
#     - schema / pydantic validation errors
#
#   These will never succeed on retry — retrying them just burns attempts
#   and delays the failure surfacing to the user. Application-layer
#   validation retry for the CD's structured output lives in
#   creative_director.py, not here.
#
# Imports are per-branch and lazy so we don't force every provider's SDK
# to be importable just to use one provider.


def _retryable_exceptions_for(
    provider: LLMProvider,
) -> tuple[type[BaseException], ...]:
    """Return the allowlist of transient-transport exception types for a provider.

    Exception types are imported lazily so missing optional provider SDKs
    don't break callers that only use a different provider.
    """
    if provider == LLMProvider.ANTHROPIC:
        from anthropic import (
            APIConnectionError,
            APITimeoutError,
            InternalServerError,
            RateLimitError,
        )
        # APITimeoutError is a subclass of APIConnectionError in the
        # anthropic SDK, but we list both for clarity.
        # 529 "overloaded" surfaces as InternalServerError (any 5xx).
        return (
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
            InternalServerError,
        )

    if provider == LLMProvider.OPENAI:
        from openai import (
            APIConnectionError,
            APITimeoutError,
            InternalServerError,
            RateLimitError,
        )
        return (
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
            InternalServerError,
        )

    if provider == LLMProvider.GOOGLE:
        # google.genai.errors exposes only APIError / ClientError / ServerError.
        # There is NO distinct RateLimitError — HTTP 429 is bundled with
        # 400 / 401 / 403 / 404 inside ClientError. Per the retry policy we
        # must not retry 4xx, so the consequence is that Google rate-limit
        # errors (429) will NOT be retried. This is a deliberate tradeoff:
        # failing loudly on auth/bad-request is safer than masking them by
        # retrying the whole ClientError family. Revisit if/when the SDK
        # grows a distinct 429 subclass.
        from google.genai.errors import ServerError
        return (ServerError,)

    return ()


def wrap_with_transport_retry(
    runnable: Runnable, provider: LLMProvider
) -> Runnable:
    """Wrap a LangChain runnable with transport-level retries.

    Applies exponential backoff with jitter (LangChain's default) for up
    to LLM_MAX_RETRIES attempts. Only the per-provider allowlist of
    transient transport errors triggers a retry — see
    _retryable_exceptions_for() for the exact set and the deliberate
    exclusions.

    Args:
        runnable: The runnable to wrap. May be a BaseChatModel or any
            composed runnable (e.g. model.with_structured_output(...)).
        provider: Which provider's exception allowlist to apply.

    Returns:
        A new runnable that retries on the allowlisted exceptions. If
        the provider has no retryable exceptions defined (unreachable
        today), the runnable is returned unchanged.
    """
    exception_types = _retryable_exceptions_for(provider)
    if not exception_types:
        return runnable
    return runnable.with_retry(
        retry_if_exception_type=exception_types,
        stop_after_attempt=LLM_MAX_RETRIES,
    )


# ---------------------------------------------------------------------------
# Chat model factory
# ---------------------------------------------------------------------------


def get_llm(
    provider: LLMProvider | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    with_retry: bool = True,
) -> Runnable:
    """Return a LangChain chat model for the specified provider.

    By default the returned runnable is wrapped with transport-level
    retries (exponential backoff, per-provider exception allowlist).
    This means every agent that calls get_llm() gets resilience to
    transient network / rate-limit / 5xx errors for free, without
    having to think about retry logic at the agent level.

    The retry wrapper uses Runnable.with_retry(), which returns a
    RunnableRetry — not a BaseChatModel. That means BaseChatModel-only
    methods such as .with_structured_output() are NOT available on the
    wrapped result. Callers that need to compose those methods should
    pass with_retry=False to get the raw BaseChatModel, apply the
    method, and then wrap the composed runnable with
    wrap_with_transport_retry() manually. The Creative Director does
    exactly this because its evaluation path uses structured output.

    Args:
        provider: Which LLM provider to use. Defaults to the value
            from config / environment.
        model: Model name override. When provided (e.g. from the
            frontend sidebar selector), this is used directly instead
            of reading from config. When None, falls back to
            get_model_name(provider) as before.
        temperature: Sampling temperature. Higher values produce more
            creative output.
        with_retry: When True (the default), the returned chat model
            is wrapped with transport-level retries. Set to False when
            you need to compose BaseChatModel-only methods such as
            .with_structured_output() on the raw model before wrapping.

    Returns:
        A LangChain runnable ready to use with .invoke(), .stream(),
        etc. When with_retry is True the concrete type is RunnableRetry;
        when False it is the provider-specific BaseChatModel subclass.
    """
    provider = provider or get_llm_provider()
    model_name = model or get_model_name(provider)

    chat_model: BaseChatModel
    if provider == LLMProvider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic

        chat_model = ChatAnthropic(
            model=model_name,
            temperature=temperature,
        )
    elif provider == LLMProvider.GOOGLE:
        from langchain_google_genai import ChatGoogleGenerativeAI

        chat_model = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
        )
    elif provider == LLMProvider.OPENAI:
        from langchain_openai import ChatOpenAI

        chat_model = ChatOpenAI(
            model=model_name,
            temperature=temperature,
        )
    else:
        # Unreachable via the enum, but guards against future additions
        # that aren't wired up yet.
        valid = ", ".join(p.value for p in LLMProvider)
        raise ValueError(
            f"Unsupported provider '{provider}'. Must be one of: {valid}"
        )

    if not with_retry:
        return chat_model
    return wrap_with_transport_retry(chat_model, provider)
