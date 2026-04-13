"""
agt_sea — LLM Provider Unit Tests

Unit tests for the transport-level retry wrapper in llm/provider.py.

Run with:
    uv run pytest tests/test_llm_provider.py

These are proper unit tests (mocked, fast, no real LLM calls) — unlike
the integration tests in test_pipeline.py / test_strategist.py / etc.
which hit real provider APIs and are meant to be driven interactively.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from anthropic import APIConnectionError
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import BaseModel

from agt_sea.llm.provider import wrap_with_transport_retry
from agt_sea.models.state import LLMProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _transient_connection_error() -> APIConnectionError:
    """Build a real anthropic.APIConnectionError for use as a retryable exception.

    The anthropic SDK exception requires an httpx.Request, so we construct
    a throwaway one — the URL and body don't matter for the test.
    """
    return APIConnectionError(request=httpx.Request("POST", "https://example.test"))


class _FlakyChatModel(BaseChatModel):
    """Minimal BaseChatModel that raises a retryable error N times, then succeeds.

    Used to verify that wrap_with_transport_retry() actually retries on the
    per-provider allowlisted exception types and that the underlying call
    only succeeds when the retry budget permits.
    """

    call_count: int = 0
    fail_times: int = 1
    response_text: str = "ok"

    @property
    def _llm_type(self) -> str:
        return "flaky"

    def _generate(
        self,
        messages: list[Any],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise _transient_connection_error()
        return ChatResult(
            generations=[
                ChatGeneration(message=AIMessage(content=self.response_text))
            ]
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_wrap_with_transport_retry_retries_on_transient_error() -> None:
    """Retries on an allowlisted exception and succeeds on the second attempt."""
    model = _FlakyChatModel(fail_times=1, response_text="recovered")

    wrapped = wrap_with_transport_retry(model, LLMProvider.ANTHROPIC)

    result = wrapped.invoke([HumanMessage(content="hi")])

    assert isinstance(result, AIMessage)
    assert result.content == "recovered"
    # First call raises, second call succeeds — exactly one retry.
    assert model.call_count == 2


def test_wrap_with_transport_retry_composes_with_structured_output() -> None:
    """Retry wraps cleanly around .with_structured_output() on a real chat model.

    This is the interop we rely on in the Creative Director: the base model
    produces a RunnableSequence via .with_structured_output(), and that
    sequence must still be retry-wrappable and still retry on transient
    errors raised from the underlying model's _generate call.
    """

    class _Eval(BaseModel):
        score: int
        label: str

    # Real ChatAnthropic so with_structured_output() exercises the real
    # tool-calling composition path. No network call happens because we
    # monkey-patch _generate below.
    base = ChatAnthropic(model="claude-sonnet-4-6", anthropic_api_key="test")

    call_count = {"n": 0}

    def flaky_generate(
        messages: list[Any],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise _transient_connection_error()
        # Return a tool_use message shaped for .with_structured_output()'s
        # default tool-calling parser.
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "call_1",
                                "name": "_Eval",
                                "args": {"score": 42, "label": "hello"},
                            }
                        ],
                    )
                )
            ]
        )

    base._generate = flaky_generate  # type: ignore[method-assign]

    composed = wrap_with_transport_retry(
        base.with_structured_output(_Eval),
        LLMProvider.ANTHROPIC,
    )

    result = composed.invoke([HumanMessage(content="evaluate this")])

    assert isinstance(result, _Eval)
    assert result.score == 42
    assert result.label == "hello"
    # First call raises, second call succeeds — exactly one retry through
    # the structured-output parser chain.
    assert call_count["n"] == 2


if __name__ == "__main__":
    # Allow running directly like the other scripts in this folder, even
    # though pytest is the preferred entry point.
    pytest.main([__file__, "-v"])
