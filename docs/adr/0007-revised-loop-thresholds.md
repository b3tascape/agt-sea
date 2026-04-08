# ADR 0007: Revised Creative Loop Thresholds

**Status:** Accepted
**Date:** 2026-04-07
**Supersedes:** [ADR 0006](0006-iterative-loop-design.md) (thresholds only — the two-gate loop design and termination logic from 0006 remain in force)

## Context

ADR 0006 established the iterative creative loop with two termination conditions: an approval threshold on the Creative Director's score, and a hard cap on iterations. It set those values at **85/100** and **5 iterations** respectively, with the acknowledgement that both were provisional and would need calibration once real runs across providers were available.

After running the pipeline against live briefs across Anthropic, Google, and OpenAI models, two things became clear:

1. **LLM creative scoring clusters in the 70–85 range.** Scores above 85 are rare even for work a human CD would consider strong, and an 85 threshold effectively guarantees the loop runs to exhaustion on most briefs. This pushes cost up without a corresponding quality gain and makes `MAX_ITERATIONS_REACHED` the default exit rather than the exception.
2. **Quality gains flatten after iteration 2–3.** The delta between iteration 1 and iteration 2 is meaningful; the delta between iteration 3 and iteration 4 is marginal and often noise. Iterations 4 and 5 were rarely producing materially better work, just more API calls.

The live code and frontend defaults were updated to 80 and 3 during development, but ADR 0006 was not revised, creating a drift between the accepted decision record and the actual system behaviour.

## Decision

Revise the default loop thresholds:

- **Approval threshold:** `80.0` (was `85.0`)
- **Max iterations:** `3` (was `5`)

Both remain configurable per run via `AgencyState.approval_threshold` and `AgencyState.max_iterations`, and both are surfaced in the sidebar for user override. The two-gate routing structure, `MAX_ITERATIONS_REACHED` best-of-fallback behaviour, and all other design decisions from ADR 0006 remain unchanged.

## Consequences

- **Positive:** Approval becomes a realistic outcome rather than an edge case. The loop exits on `APPROVED` for most briefs where the work genuinely meets the bar, which is the intended happy path.
- **Positive:** Worst-case cost per run drops from 5 to 3 creative iterations (plus strategist and final CD pass). Meaningful when running on frontier models and when testing across providers.
- **Positive:** The accepted ADRs now match the code, removing a source of confusion for anyone onboarding to the project.
- **Negative:** An 80 threshold is still arbitrary and still needs periodic recalibration as models evolve. Future structured logging (Phase 6.2) will produce the score distributions needed to tune this further.
- **Negative:** A 3-iteration cap is tighter than 5. Briefs that would have reached approval on iteration 4 under the old cap will now exit via `MAX_ITERATIONS_REACHED` with the best-of fallback. Acceptable given the cost tradeoff and the observation that iteration-4 gains were marginal in practice.
- **Neutral:** This ADR supersedes 0006's threshold values only. ADR 0006 remains the canonical record for the loop's structural design. Per the project's append-only ADR rule, 0006 is not edited — its status line should be updated to reference this supersession, and the index should reflect it.
