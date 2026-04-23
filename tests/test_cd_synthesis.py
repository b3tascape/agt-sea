"""
agt_sea — CD Synthesis Schema Unit Tests

Unit tests (pytest, mocked, no real LLM calls) covering the Pydantic
schema contract for ``CDSynthesis`` and its nested ``ConceptScoreSummary``.

Validation-retry behaviour is *not* re-tested here — it's generic over
any Pydantic model and already covered by ``test_cd_grader.py`` (which
binds ``invoke_with_validation_retry`` to a second schema besides the
original ``CDEvaluation``). This file focuses purely on the data
contract: required fields, score bounds, ``comparison_notes`` default.

Run with:
    uv run pytest tests/test_cd_synthesis.py
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agt_sea.models.state import CDSynthesis, ConceptScoreSummary


# ---------------------------------------------------------------------------
# ConceptScoreSummary
# ---------------------------------------------------------------------------


def test_concept_score_summary_accepts_valid_payload() -> None:
    summary = ConceptScoreSummary(
        title="Hours off the clock",
        score=82.5,
        assessment="On-strategy with a distinctive core idea.",
    )
    assert summary.title == "Hours off the clock"
    assert summary.score == 82.5


def test_concept_score_summary_rejects_score_above_100() -> None:
    with pytest.raises(ValidationError):
        ConceptScoreSummary(title="over", score=101, assessment="ok")


def test_concept_score_summary_rejects_score_below_zero() -> None:
    with pytest.raises(ValidationError):
        ConceptScoreSummary(title="under", score=-0.1, assessment="ok")


def test_concept_score_summary_requires_all_fields() -> None:
    """title, score, and assessment have no defaults — all three required."""
    with pytest.raises(ValidationError):
        ConceptScoreSummary.model_validate({"title": "x", "score": 50})
    with pytest.raises(ValidationError):
        ConceptScoreSummary.model_validate({"title": "x", "assessment": "x"})
    with pytest.raises(ValidationError):
        ConceptScoreSummary.model_validate({"score": 50, "assessment": "x"})


# ---------------------------------------------------------------------------
# CDSynthesis — single-concept branch
# ---------------------------------------------------------------------------


def test_cd_synthesis_single_concept_with_none_comparison_notes() -> None:
    """Simplified v2 graph: one concept, comparison_notes omitted (→ None)."""
    synthesis = CDSynthesis(
        selected_title="Hours off the clock",
        recommendation="This is the concept we take forward because...",
        score_summary=[
            ConceptScoreSummary(
                title="Hours off the clock",
                score=82.0,
                assessment="On-strategy and distinctive.",
            )
        ],
    )
    assert synthesis.comparison_notes is None
    assert len(synthesis.score_summary) == 1


def test_cd_synthesis_multi_concept_with_comparison_notes() -> None:
    """Future parallel variant: N concepts, comparison_notes populated."""
    synthesis = CDSynthesis(
        selected_title="Concept A",
        recommendation="We recommend A because...",
        score_summary=[
            ConceptScoreSummary(title="Concept A", score=85, assessment="best"),
            ConceptScoreSummary(title="Concept B", score=71, assessment="ok"),
        ],
        comparison_notes="A edges out B because the core idea lands harder.",
    )
    assert synthesis.comparison_notes is not None
    assert len(synthesis.score_summary) == 2


# ---------------------------------------------------------------------------
# CDSynthesis — required fields
# ---------------------------------------------------------------------------


def test_cd_synthesis_requires_selected_title() -> None:
    with pytest.raises(ValidationError):
        CDSynthesis.model_validate({"recommendation": "x"})


def test_cd_synthesis_requires_recommendation() -> None:
    with pytest.raises(ValidationError):
        CDSynthesis.model_validate({"selected_title": "x"})


def test_cd_synthesis_score_summary_defaults_to_empty_list() -> None:
    """score_summary has a default_factory — callers can omit it.

    The *prompt* instructs the LLM to always populate score_summary, but
    the schema itself doesn't require it. This test locks in that
    schema-level behaviour so a future tightening of the prompt doesn't
    accidentally get coupled to a schema change.
    """
    synthesis = CDSynthesis(selected_title="x", recommendation="y")
    assert synthesis.score_summary == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
