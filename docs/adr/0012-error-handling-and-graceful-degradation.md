# ADR 0012: Error Handling and Graceful Degradation

**Status:** Accepted
**Date:** 2026-04-14

## Context

Before Phase 6.1, the pipeline had no error handling worth the name. A transient 529 from Anthropic, a Google rate-limit bounce, a brief network blip, or a Creative Director response that didn't conform to the `CDEvaluation` schema all surfaced as the same thing: a Python traceback rendered straight into the Streamlit page. Three gaps in particular:

1. **No retries.** LLM calls were one-shot. A 2-second network hiccup mid-run threw away the entire pipeline state, including however many iterations had already been paid for.
2. **No failure contract between graph and frontend.** `AgencyState.status` had `APPROVED` and `MAX_ITERATIONS_REACHED` but no `FAILED`. The frontend had nowhere to read a failure from, so pages rendered whatever garbage state came back from a crashed run and eventually exploded on a `None` attribute.
3. **No separation between "transient and worth retrying" and "terminal, surface to user".** Every exception was terminal and every terminal exception was a traceback. A 401 auth failure and a 529 overloaded error were treated identically — both crashed the page, both forced the user to restart the run with no idea what had happened.

The work also had to stay inside bounded scope. Phase 6.1 is about resilience, not recovery. Checkpointing, cross-provider fallback, token budgets, and rate-limiting are all adjacent concerns that were deliberately pushed out (see Non-goals below) to keep this workstream shippable and to avoid pre-committing to architecture that other Phase 6 workstreams should own.

Alternatives considered for the overall shape:

- **Global try/except around `graph.invoke()` in every frontend page.** Cheapest possible fix. Catches everything, loses the *which agent* context, and doesn't help tests or non-frontend callers. Pushes the same try/except into three pages that then need to agree on an error format by convention.
- **Decorators on agent functions.** Put the retry + failure capture on each `run_*` function directly. Pollutes agent files with resilience concerns, obscures where the orchestration boundary is, and forces every new agent to opt in (or silently miss out).
- **Cross-provider fallback.** On a hard failure, automatically re-run with the next provider. Rejected — the project's provider-comparison use case depends on a single run being attributable to a single provider. See Non-goals.
- **Two-layer retry at the orchestration layer + a `FAILED` contract.** The decision below.

## Decision

Five decisions, all committed together in Phase 6.1 Steps 2–6.

### 1. Retry-only fallback policy

Transient failures retry on the same provider and model with backoff. Persistent failures surface to the user with provider/model context so they can choose to switch and re-run manually. No automatic cross-provider or cross-model fallback.

Backoff behaviour is LangChain's default exponential-backoff-with-jitter — `wrap_with_transport_retry()` passes only `retry_if_exception_type` and `stop_after_attempt=LLM_MAX_RETRIES` to `.with_retry()`, so timing specifics are owned by the framework, not this ADR. The count is a live knob (`LLM_MAX_RETRIES`, default 3) and can be overridden via env or Streamlit secrets.

The reasoning for retry-only (no provider / model fallback) is not performance, it is artefact coherence. The pipeline compares CD scores across iterations to decide when to stop, and different models score creative work on different curves — a mid-run swap from Sonnet to Haiku would silently compare scores that aren't on the same scale. For the same reason, provider comparison (a first-class use case once the Tools module ships) requires that "this run used Anthropic" remains true for the whole run, not "this run used Anthropic except for the iteration where it retried against OpenAI because the first attempt flaked." Loud failures preserve attributability; quiet fallbacks destroy it.

### 2. Two-layer retry model

Retries are split across two layers, placed where the exception semantics actually live.

- **Transport layer — `get_llm()`.** Network errors, HTTP 429, Anthropic 529, and HTTP 503 are framework-level cross-cutting concerns. They happen inside the LangChain chat model, they're not specific to any one agent, and the knob that bounds them (`LLM_MAX_RETRIES`) is a deployment concern. A `wrap_with_transport_retry()` helper in `llm/provider.py` applies `.with_retry()` to the returned chat model with an explicit per-provider allowlist. Every caller gets retries for free; agents stay clean.
- **Application layer — `creative_director.py`.** Schema-validation failures on `CDEvaluation` are not transient. They happen *after* a successful network call, when `with_structured_output()`'s parser tries to build a `CDEvaluation` from the model response and the model returned something that doesn't conform. Retrying the same request won't help — the LLM has to see what it got wrong. A module-private `_invoke_with_validation_retry()` helper catches `pydantic.ValidationError`, reprompts once with the error text appended as a new `HumanMessage`, and calls `.invoke()` once more. If the second attempt also fails, the exception propagates to the orchestration layer.

The layer boundary is forced by LangChain: `.with_retry()` returns a `RunnableRetry`, which has no `.with_structured_output()` method. Wrap order must be `structured_output → retry`, not the other way around. The CD composes manually:

```python
llm = get_llm(provider=provider, model=model, with_retry=False)
structured_llm = wrap_with_transport_retry(
    llm.with_structured_output(CDEvaluation), provider
)
evaluation = _invoke_with_validation_retry(structured_llm, messages)
```

From the validation-retry helper's perspective, each `.invoke()` is a single attempt — inside that attempt, transport retries may fire zero or more times.

### 3. Explicit retryable exception set

`.with_retry()` defaults to retrying on *any* exception. This default is rejected. The retry allowlist is defined per provider in `_retryable_exceptions_for()` (in `llm/provider.py`) and includes only:

- **Anthropic** (`anthropic` SDK): `APIConnectionError`, `APITimeoutError`, `RateLimitError`, `InternalServerError` (the last covers 5xx including the 529 "overloaded" status).
- **OpenAI** (`openai` SDK): same four.
- **Google** (`google.genai.errors`): `ServerError` only. The Google GenAI SDK exposes just `APIError` / `ClientError` / `ServerError` — there is no distinct `RateLimitError`, and HTTP 429 is bundled into `ClientError` alongside 400 / 401 / 403 / 404. Per the retry policy we must not retry 4xx, so the consequence is that Google rate-limit errors will not be retried. This is a deliberate tradeoff documented inline in `provider.py` and should be revisited if the SDK grows a distinct 429 subclass.

Auth errors (401/403), schema/validation errors, and all other 4xx client errors are explicitly excluded from every provider's allowlist because they will never succeed on retry — retrying them just burns attempts and delays the failure surfacing. The exclusion is deliberate, not oversight, and is commented as such in `provider.py`.

### 4. `FAILED` status and `error` field as the contract between graph and frontend

`WorkflowStatus.FAILED` was added to the enum and `error: str | None` was added to `AgencyState`. Together they form the contract: any node that fails populates `error`, and routing diverts to a `finalise_failed` node that sets `status = FAILED`. The frontend reads these after rehydration and renders an error component instead of agent output.

The error-string format — `"<agent_fn> failed: <ExcType>: <msg>"` — is a three-site display contract: `_safe_node` (the producer), `frontend/components/error_state.py` (the consumer, display-only), and the standalone Strategy / Creative frontend pages (which call agents directly outside the graph and reconstruct the same string on failure). To prevent drift across the three sites, the format is owned by a single helper, `format_node_error(fn_name, exc)`, that lives next to `_safe_node` in `graph/workflow.py` and is imported by both the safe wrapper and the standalone pages.

### 5. Safe-node wrapper at graph-build time, not decorators on agents or try/except inside agents

Try/except lives at the orchestration layer. Agent functions stay completely untouched. In `graph/workflow.py`, each agent node is wrapped at graph-build time with a `_safe_node()` higher-order helper that catches escaped exceptions, writes the error to state via `format_node_error`, and returns the state. Routing functions stay pure — each one begins with a uniform error guard:

```python
if state.error is not None:
    return "failed"
```

applied across strategist, creative, and Creative Director routing. The guard reads state and returns a string; no mutation, no side effect. The mutation already happened in `_safe_node`.

The alternative — widening `check_approval` into a three-way return that mixes failure with approval logic, or adding a pre-check routing node just for the CD — was rejected because it would break the single-responsibility naming of the existing routing functions and would introduce an asymmetry between the CD's routing (which has business logic) and the strategist's / creative's (which don't). Uniformity at the top of every routing function was chosen over per-site specialisation.

## Consequences

- **Positive:** Transient LLM failures no longer crash runs. A flaky network, a 429, or a 529 now gets retried automatically with the provider's allowlist, inside bounds set by `LLM_MAX_RETRIES`. Users stop seeing tracebacks for problems that resolve themselves in two seconds.
- **Positive:** Hard failures become a UX, not a stack trace. The three frontend pages (workflow, strategy, creative) render an `error_state` component with the error message, provider, model, and a hint to retry or switch — matching theme, no traceback.
- **Positive:** Resilience is visible at the orchestration layer, not scattered through agent files. A future reader can look at `build_graph()` and see exactly which nodes are wrapped, which routing functions guard on `state.error`, and how failures terminate. Agents stay clean and new agents inherit the wrapper by construction.
- **Positive:** The `FAILED` contract is a clean integration point for Phase 6.4 (structured logging / tracing). `state.error` is already populated with a stable format at the moment of failure, so a logging hook in `_safe_node` gets everything it needs for free.
- **Positive:** Phase 6.2 (human-in-the-loop with interrupt/resume) inherits the contract unchanged. A paused run that later fails on resume will populate `state.error` and route to `finalise_failed` the same way an unpaused run does. No additional integration work.
- **Negative:** LangChain coupling deepens. The retry layer, the per-provider exception allowlist, and the `.with_retry() → RunnableRetry → can't .with_structured_output()` workaround are all LangChain-specific shapes. A future migration away from LangChain would need to re-implement all of this. Accepted — LangChain is the chosen abstraction (ADR 0002) and the integration is already load-bearing.
- **Negative:** The retry policy is a live knob that will need tuning. `LLM_MAX_RETRIES = 3` is a starting point, not a derived optimum. The per-provider allowlists are narrow on purpose but may need to widen (e.g. if Google ever distinguishes a retryable server-side subclass of `ClientError`). The ADR fixes the *shape* of the policy, not the values.
- **Negative:** No recovery from mid-run failures. If the CD crashes on iteration 2, the run ends — the partial strategist + iteration 1 work is not reusable. Acceptable for this phase; checkpointing is the Phase 6.2 concern that addresses this.
- **Neutral:** The error format is a display contract, not a parse contract. `error_state.py` renders `state.error` verbatim via `st.error()` — it never inspects the shape. The only substring consumers today are the failure tests (`test_pipeline_failure.py`), which assert that specific tokens appear in the error string. If the format ever needs to become structured (provider, model, exception type, traceback, all as separate fields), the change is additive for the frontend — a richer `state.error` type would continue to render correctly — and only the tests would need updating to match the new shape. Flagged for Phase 6.4 if structured logging needs it.
- **Neutral:** Sets the pattern for future agents. A new agent (e.g. a Marketing module specialist) gets transport retries for free from `get_llm()`, gets orchestration-layer safety for free from `_safe_node`, and only has to respect the failure contract by not swallowing its own exceptions. The expected authoring cost for resilience on a new agent is zero.
- **Neutral:** Adds a `pytest`-based unit-test layer to the project alongside the existing manual integration tests. `test_llm_provider.py`, `test_creative_director_retry.py`, and `test_pipeline_failure.py` were all introduced during this work and establish the convention for future unit tests. The full-pipeline integration test (`test_pipeline.py`) remains manual and still makes real LLM calls.

## Non-goals

These were explicitly out of scope for Phase 6.1 and remain so. They are not rejected — they are deferred, each with a specific home.

- **Cross-provider fallback (Anthropic → Google → OpenAI on hard failure).** Rejected on artefact-coherence grounds (see Decision 1). Will not be revisited.
- **Same-provider model fallback (Sonnet → Haiku).** Same reasoning — different models score creative work on different curves and the loop compares scores across iterations. Will not be revisited.
- **Checkpointing and partial-run recovery.** Deferred to Phase 6.2 (human-in-the-loop), which will introduce LangGraph's checkpointer to support interrupt/resume. The `FAILED` contract established here will remain the failure surface on checkpointed runs.
- **Cross-cutting token budgeting.** Deferred to Phase 6.4 (structured logging / tracing). Cost protection at the project's current scale is already covered by `max_iterations` (bounds loop length) and provider spend caps (bounds monthly spend). Token accounting is observability, not protection.
- **Rate limiting and abuse mitigation.** Separate mini-workstream with its own ADR when the app graduates beyond personal / portfolio use. No session counters or per-IP limits in this phase.
- **Circuit breakers.** Premature for current scale. The retry allowlist plus `LLM_MAX_RETRIES` bound gives an adequate cap on wasted attempts without the added state of a circuit breaker.
