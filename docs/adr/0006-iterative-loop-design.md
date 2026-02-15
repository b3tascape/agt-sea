# ADR 0006: Iterative Creative Loop with Bounded Execution

**Status:** Accepted  
**Date:** 2026-02-15

## Context

The agent graph includes a feedback loop: the Creative Director evaluates the Creative agent's output and either approves it or sends it back for revision. This loop must have explicit termination conditions to prevent infinite execution and runaway API costs.

The routing logic requires two sequential decisions:

1. Does the creative work meet the quality threshold?
2. If not, has the iteration limit been reached?

These are modelled as two distinct conditional nodes in the graph.

## Decision

The creative loop terminates when **either** condition is met:

1. **Approval:** The Creative Director's `cd_score` meets or exceeds the `approval_threshold` (default: 80/100). Status is set to `APPROVED`. The current creative concept is returned as the final output.
2. **Max iterations:** The loop has executed `max_iterations` times (default: 5). Status is set to `MAX_ITERATIONS_REACHED`. The system selects the **highest-scoring creative concept** from the iteration history and returns it as the final output, with a clear indication that it was not formally approved but represents the best work produced within the iteration budget.

Both thresholds are configurable fields on `AgencyState` and can be adjusted per run.

## Consequences

- **Positive:** Guarantees termination. Worst case is 5 iterations, which bounds both execution time and API cost.
- **Positive:** The two-gate routing (score check → iteration check) is explicit in the graph architecture, making the system's behaviour predictable and debuggable.
- **Positive:** `MAX_ITERATIONS_REACHED` still delivers a useful output — the best available creative — rather than failing silently. The user receives the strongest work produced alongside its score and the full iteration history showing progression.
- **Positive:** Two distinct output paths (approved vs. best-of) allow the frontend to communicate the outcome clearly, e.g., a warning indicator on outputs that didn't reach the approval threshold.
- **Negative:** A fixed iteration cap is blunt. The system might be one iteration away from approval when it hits the limit. Acceptable for v1; future versions could allow the user to extend.
- **Negative:** The 80% threshold is somewhat arbitrary. Will need calibration based on how different LLMs score creative work. Structured logging of scores across runs will inform tuning.
- **Negative:** Selecting the "best" iteration requires comparing scores across history, adding minor complexity to the exit logic.