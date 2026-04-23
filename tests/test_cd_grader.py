"""
agt_sea — CD Grader Unit Tests

Unit tests (pytest, mocked, no real LLM calls) covering:

1. ``GraderEvaluation`` schema validation — score bounds, required fields,
   and type coercion. Proves the Pydantic contract Creative 2's loop
   relies on.
2. ``invoke_with_validation_retry`` exercised against ``GraderEvaluation``.
   The helper is generic over Pydantic models; test_creative_director_retry
   covers the happy path with ``CDEvaluation``. This test binds the
   TypeVar to a second schema to guard against regressions in the
   generalisation.

Run with:
    uv run pytest tests/test_cd_grader.py
"""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import ValidationError

from agt_sea.llm.provider import invoke_with_validation_retry
from agt_sea.models.state import GraderEvaluation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeStructuredLLM:
    """Minimal stand-in for the composed structured-output runnable.

    Duck-typed ``.invoke(messages)`` — ``results`` is a scripted queue:
    exceptions are raised, values are returned. Each call records the
    messages it saw on ``.calls`` for inspection.
    """

    def __init__(self, results: list[Any]) -> None:
        self._results = list(results)
        self.calls: list[list[BaseMessage]] = []

    def invoke(self, messages: list[BaseMessage]) -> GraderEvaluation:
        self.calls.append(messages)
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _make_grader_validation_error() -> ValidationError:
    """Build a real pydantic ValidationError by feeding GraderEvaluation junk."""
    try:
        GraderEvaluation.model_validate({"score": "not a number"})
    except ValidationError as exc:
        return exc
    raise RuntimeError("expected GraderEvaluation.model_validate to raise")


def _valid_grade() -> GraderEvaluation:
    return GraderEvaluation(
        score=74,
        rationale="Solid core idea, execution specificity falls off in the final two deliverables.",
    )


def _base_messages() -> list[BaseMessage]:
    return [
        SystemMessage(content="you are a grader"),
        HumanMessage(content="score this"),
    ]


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def test_grader_evaluation_accepts_valid_payload() -> None:
    """Happy-path schema parse — nothing fancy, just proves the shape."""
    ev = GraderEvaluation(score=82, rationale="On-strategy with minor gaps.")
    assert ev.score == 82
    assert "On-strategy" in ev.rationale


def test_grader_evaluation_rejects_score_above_100() -> None:
    with pytest.raises(ValidationError):
        GraderEvaluation(score=101, rationale="over")


def test_grader_evaluation_rejects_score_below_zero() -> None:
    with pytest.raises(ValidationError):
        GraderEvaluation(score=-1, rationale="under")


def test_grader_evaluation_requires_rationale() -> None:
    """rationale has no default — the grader must always justify the score."""
    with pytest.raises(ValidationError):
        GraderEvaluation.model_validate({"score": 50})


def test_grader_evaluation_requires_score() -> None:
    """score has no default — the grader must always produce a number."""
    with pytest.raises(ValidationError):
        GraderEvaluation.model_validate({"rationale": "ok"})


def test_grader_evaluation_score_coerces_ints() -> None:
    """Float field with an int payload — pydantic should coerce cleanly."""
    ev = GraderEvaluation(score=75, rationale="fine")
    assert isinstance(ev.score, float)
    assert ev.score == 75.0


# ---------------------------------------------------------------------------
# Validation retry bound to GraderEvaluation
# ---------------------------------------------------------------------------


def test_retry_transparent_on_first_grader_success() -> None:
    """Happy path with GraderEvaluation: one call, no reprompt."""
    valid = _valid_grade()
    fake = _FakeStructuredLLM(results=[valid])
    messages = _base_messages()

    result = invoke_with_validation_retry(fake, messages)

    assert result is valid
    assert len(fake.calls) == 1
    assert fake.calls[0] == messages


def test_retry_succeeds_on_second_attempt_with_grader() -> None:
    """ValidationError then success: asserts the reprompt lands on
    the second call with the error text interpolated in, just like the
    CDEvaluation path."""
    error = _make_grader_validation_error()
    valid = _valid_grade()
    fake = _FakeStructuredLLM(results=[error, valid])
    messages = _base_messages()
    original_len = len(messages)

    result = invoke_with_validation_retry(fake, messages)

    assert result is valid
    assert len(fake.calls) == 2
    assert fake.calls[0] == messages

    second_call = fake.calls[1]
    assert len(second_call) == original_len + 1
    assert second_call[:original_len] == messages

    appended = second_call[-1]
    assert isinstance(appended, HumanMessage)
    assert str(error) in appended.content
    assert "failed schema validation" in appended.content


def test_retry_propagates_second_grader_failure() -> None:
    """Two consecutive ValidationErrors propagate — the safe-node wrapper
    surfaces this as a FAILED run."""
    fake = _FakeStructuredLLM(
        results=[_make_grader_validation_error(), _make_grader_validation_error()]
    )

    with pytest.raises(ValidationError):
        invoke_with_validation_retry(fake, _base_messages())

    assert len(fake.calls) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
