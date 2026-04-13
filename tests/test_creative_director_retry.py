"""
agt_sea — Creative Director Validation Retry Unit Tests

Unit tests for `_invoke_with_validation_retry` in
`agt_sea.agents.creative_director`.

Run with:
    uv run pytest tests/test_creative_director_retry.py

These are proper unit tests (mocked, fast, no real LLM calls) — the helper
is fed a tiny fake ``structured_llm`` object that scripts a sequence of
return values and exceptions, mirroring the convention set by
``tests/test_llm_provider.py`` in Step 3 of Phase 6.1.
"""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import ValidationError

from agt_sea.agents.creative_director import _invoke_with_validation_retry
from agt_sea.models.state import CDEvaluation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeStructuredLLM:
    """Minimal stand-in for the composed structured-output runnable.

    The helper only needs something with an ``.invoke(messages)`` method,
    so we duck-type rather than constructing a real Runnable. ``results``
    is a list of scripted outputs: exceptions are raised, values are
    returned. Each call to ``.invoke()`` pops the next entry and records
    the messages it received in ``.calls`` for later inspection.
    """

    def __init__(self, results: list[Any]) -> None:
        self._results = list(results)
        self.calls: list[list[BaseMessage]] = []

    def invoke(self, messages: list[BaseMessage]) -> CDEvaluation:
        self.calls.append(messages)
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _make_validation_error() -> ValidationError:
    """Build a real pydantic ValidationError by feeding CDEvaluation junk."""
    try:
        CDEvaluation.model_validate(
            {"score": "not a number", "direction": "ok"}
        )
    except ValidationError as exc:
        return exc
    raise RuntimeError("expected CDEvaluation.model_validate to raise")


def _valid_evaluation() -> CDEvaluation:
    return CDEvaluation(
        score=82,
        strengths=["clear insight"],
        weaknesses=["execution vague"],
        direction="Tighten the hero film brief.",
    )


def _base_messages() -> list[BaseMessage]:
    return [
        SystemMessage(content="you are a CD"),
        HumanMessage(content="evaluate this"),
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_validation_retry_transparent_on_first_success() -> None:
    """Happy path: a valid response on the first call means no reprompt.

    Locks in the contract that the helper is transparent when validation
    succeeds — exactly one invocation, the returned value is whatever
    came back, and no extra messages are constructed.
    """
    valid = _valid_evaluation()
    fake = _FakeStructuredLLM(results=[valid])
    messages = _base_messages()

    result = _invoke_with_validation_retry(fake, messages)

    assert result is valid
    assert len(fake.calls) == 1
    # Message list must be passed through unchanged on the happy path.
    assert fake.calls[0] == messages


def test_validation_retry_succeeds_on_second_attempt() -> None:
    """First call raises ValidationError, second returns a valid evaluation.

    Asserts the helper returns the valid evaluation AND that the reprompt
    is shaped correctly: exactly one new message appended, of type
    HumanMessage, with the ValidationError text interpolated in.
    """
    error = _make_validation_error()
    valid = _valid_evaluation()
    fake = _FakeStructuredLLM(results=[error, valid])
    messages = _base_messages()
    original_len = len(messages)

    result = _invoke_with_validation_retry(fake, messages)

    assert result is valid
    assert len(fake.calls) == 2

    # First call sees the untouched original prompt.
    assert fake.calls[0] == messages

    # Second call appends exactly one message — nothing more, nothing less.
    second_call = fake.calls[1]
    assert len(second_call) == original_len + 1
    assert second_call[:original_len] == messages

    # The appended message must be a HumanMessage carrying the
    # ValidationError text (proves interpolation actually happened, not
    # just that *some* reprompt was added).
    appended = second_call[-1]
    assert isinstance(appended, HumanMessage)
    assert str(error) in appended.content
    assert "failed schema validation" in appended.content


def test_validation_retry_propagates_second_failure() -> None:
    """Two consecutive ValidationErrors propagate to the caller.

    The second failure is not caught — it's the orchestration-layer
    safe-node wrapper's job (Step 5) to surface this as a FAILED run.
    """
    error_one = _make_validation_error()
    error_two = _make_validation_error()
    fake = _FakeStructuredLLM(results=[error_one, error_two])

    with pytest.raises(ValidationError):
        _invoke_with_validation_retry(fake, _base_messages())

    assert len(fake.calls) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
