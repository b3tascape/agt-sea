# Phase 6.1 — Error Handling & Graceful Degradation

**Status:** In progress
**Owner:** @b3tascape
**Related ADR:** 0012 (to be written as final step)

## Goal

Make the agt_sea pipeline resilient to transient LLM failures and surface hard failures cleanly to the user instead of crashing the Streamlit page. Two layers of retry (transport-level for network/rate-limit errors, application-level for CD structured-output validation), a new `FAILED` workflow status, and frontend rendering that turns tracebacks into actionable error states.

## Non-goals

These are explicitly **out of scope** for 6.1. Do not implement them, do not propose them mid-work:

- **Cross-provider fallback** (Anthropic → Google → OpenAI on hard failure). Breaks the provider-comparison use case and corrupts run artefacts. Retry only on the same provider/model; fail loudly otherwise.
- **Same-provider model fallback** (e.g. Sonnet → Haiku). Same reasoning — different models score creative work differently and the loop compares scores across iterations.
- **Checkpointing / partial-run recovery.** Belongs with Phase 6.1's human-in-the-loop work, not here.
- **Cross-cutting token budgeting.** `max_iterations` already bounds cost. Token accounting is observability (Phase 6.4), not protection.
- **Rate limiting / abuse mitigation.** Separate mini-workstream with its own ADR. Do not add session counters or per-IP limits in this phase.
- **Circuit breakers.** Premature for current scale.

## Design decisions (locked — do not re-litigate)

These were settled before work started. If something here looks wrong, raise it before coding, not by silently choosing a different option.

1. **Retry-only fallback policy.** Transient failures retry on the same provider/model with exponential backoff. Persistent failures surface to the user with provider/model context so they can choose to switch and re-run.
2. **Two-layer retry model.**
   - **Transport layer** (network errors, 429, 529, 503): `get_llm()` wraps the chat model via a `wrap_with_transport_retry()` helper in `llm/provider.py`. By default every caller gets retries automatically and agents stay clean. Callers that need to compose `.with_structured_output()` (currently just the Creative Director) pass `with_retry=False` to get the raw `BaseChatModel`, apply structured output, and then wrap the composed runnable with `wrap_with_transport_retry()` themselves. This ordering is forced by LangChain: `.with_retry()` returns a `RunnableRetry` which has no `.with_structured_output()`, so wrap order must be `structured_output → retry`, not the other way around. Proven end-to-end by `tests/test_llm_provider.py`.
   - **Application layer** (CD `CDEvaluation` validation failures): handled in `creative_director.py` via a one-shot reprompt-on-`ValidationError` helper. Lives with the agent that owns the schema.
3. **Retryable exceptions are explicit, not implicit.** `.with_retry()` defaults retry on any exception. Narrow this with `retry_if_exception_type` to transient transport errors only. Auth errors, validation errors, and 4xx client errors must NOT be retried.
4. **Failure surfacing via `AgencyState`.** New `WorkflowStatus.FAILED` value and a new `error: str | None` field on `AgencyState`. The frontend reads these after rehydration and renders an error component instead of agent output.
5. **Try/except lives at the orchestration layer, not in agents.** Agent functions stay untouched. In `graph/workflow.py`, each agent node is wrapped at graph-build time with a `_safe_node()` helper that catches escaped exceptions, writes the error to state, and lets routing send the run to a `_finalise_failed` node. Routing functions stay pure.
6. **CD validation retry is one-shot reprompt, not backoff.** Validation failures are not transient. Reprompt once with the schema error included; if the second attempt also fails, fail the run.

## Steps

Work proceeds in order. Each step ends at a commit. Run `uv run python tests/test_pipeline.py` and `uv run ruff check .` after every step. Do not start step N+1 until step N is committed.

---

### Step 1 — Provider spend caps ✅

Manual, no code. Hard monthly budget caps set in each provider's dashboard as the last-line-of-defence safety net.

- [x] Anthropic monthly cap set
- [x] Google monthly cap set
- [x] OpenAI monthly cap set
- [x] Credit auto-reload disabled across all three

---

### Step 2 — `FAILED` status and `error` field

Smallest possible data model change. Foundation for every later step.

**Files:**
- `src/agt_sea/models/state.py`
- Any file that exhaustively matches on `WorkflowStatus` (search for it)

**Changes:**
- Add `FAILED = "failed"` to the `WorkflowStatus` enum
- Add `error: str | None = None` field to `AgencyState`
- Update any `match` statements or `if/elif` chains over `WorkflowStatus` so `FAILED` is handled (even if just as a no-op for now)

**Acceptance:**
- `from agt_sea.models.state import WorkflowStatus; WorkflowStatus.FAILED` resolves
- `AgencyState().error is None` by default
- Existing tests pass unchanged
- `ruff check .` clean

**Commit message:** `feat: add FAILED status and error field to AgencyState`

---

### Step 3 — Transport-level retries in `get_llm()`

Wrap the chat model returned from `get_llm()` with `.with_retry()`. Every agent gets resilience for free.

**Files:**
- `src/agt_sea/llm/provider.py`
- `src/agt_sea/config.py` (new config knob)

**Changes:**
- Add `LLM_MAX_RETRIES` config setting with a sensible default (suggested: `3`). Read via the existing `_get_secret()` helper so it can be overridden via env or Streamlit secrets.
- In `get_llm()`, wrap the constructed chat model with `.with_retry(stop_after_attempt=N, retry_if_exception_type=...)` before returning.
- **Be explicit about retryable exception types.** Do not rely on `.with_retry()`'s default behaviour, which retries on any exception. Define two explicit lists:
  - **Retry these (allowlist):** transient transport errors only. At minimum: network errors (connection failures, timeouts), rate limit errors (HTTP 429), overloaded errors (Anthropic 529), service unavailable (HTTP 503).
  - **Do NOT retry these (must be excluded):** auth errors (HTTP 401/403), schema/validation errors, and all other 4xx client errors. These will never succeed on retry — retrying them just burns attempts and delays the failure surfacing to the user.

  Both lists must be visible in code (the allowlist passed to `retry_if_exception_type`, the denylist documented in a comment so future readers know it's deliberate exclusion, not oversight).
- Document the retry policy in a docstring on `get_llm()`.

**Note for Claude Code:** Before implementing, identify the specific exception classes for each provider and confirm them. LangChain wraps provider exceptions inconsistently — check what's actually raised on a real 429 from Anthropic vs Google vs OpenAI. If unclear, propose a conservative set and flag the uncertainty rather than guess.

**Acceptance:**
- `get_llm()` returns a model wrapped in `.with_retry()`
- Retry policy is explicit about which exceptions retry
- Existing tests pass (retry wrapper is transparent to success paths)
- `ruff check .` clean

**Commit message:** `feat: add transport-level retries to get_llm()`

---

### Step 4 — CD structured-output validation retry

Wrap the CD's `with_structured_output` call in a one-shot reprompt-on-`ValidationError` helper.

**Files:**
- `src/agt_sea/agents/creative_director.py`
- `tests/test_creative_director_retry.py` (new — small unit test)

**Changes:**
- Add a helper (private to the module, e.g. `_invoke_with_validation_retry`) that:
  1. Calls the structured-output model with the prompt
  2. On `pydantic.ValidationError`, constructs a reprompt that includes the original prompt, a brief "your previous response failed schema validation" preamble, and the validation error message
  3. Calls once more
  4. If the second call also raises, lets the exception propagate (it'll be caught by the orchestration-layer wrapper in Step 5)
- Use this helper in `run_creative_director()` instead of calling the structured-output model directly.
- Add a unit test that mocks the LLM to raise `ValidationError` on first call and return a valid `CDEvaluation` on second. Assert the retry path works and the final state contains the valid evaluation.

**Acceptance:**
- Validation failure on first attempt + success on second = clean run, no error surfaced
- Validation failure on both attempts = exception propagates (will be handled in Step 5)
- New unit test passes
- `ruff check .` clean

**Commit message:** `feat: add validation retry to creative director structured output`

---

### Step 5 — Failure nodes, safe wrappers, and routing

The biggest step. Wraps each agent node so escaped exceptions become clean `FAILED` exits instead of tracebacks.

**Files:**
- `src/agt_sea/graph/workflow.py`
- `tests/test_pipeline_failure.py` (new)

**Changes:**

1. **Add `_finalise_failed` node.** Pure node, sets `state.status = WorkflowStatus.FAILED`, ensures `state.error` is populated (if not already, set a generic message). Returns the state.

2. **Add `_safe_node()` helper.** Higher-order function that takes an agent function and returns a wrapped version:
   ```python
   def _safe_node(agent_fn):
       def wrapped(state: AgencyState) -> AgencyState:
           try:
               return agent_fn(state)
           except Exception as exc:
               state.error = f"{agent_fn.__name__} failed: {type(exc).__name__}: {exc}"
               return state
       return wrapped
   ```
   Note the agent name in the error message — the user needs to know *which* agent failed, not just *that* something failed.

3. **Wrap each agent at graph-build time.** Where the graph currently does `graph.add_node("strategist", run_strategist)`, change to `graph.add_node("strategist", _safe_node(run_strategist))`. Same for creative and creative_director.

4. **Add failure routing.** Each agent node now needs a conditional edge that checks "did this fail?" and routes to `_finalise_failed` if so, otherwise continues to the next node as before. Routing functions stay pure — they read `state.error is not None` and return a string. The mutation already happened in `_safe_node`.

5. **Wire `_finalise_failed` → `END`.**

6. **New integration test.** `tests/test_pipeline_failure.py` — mocks `run_strategist` (or one of the agents) to raise an exception, runs the graph, asserts the final rehydrated state has `status == FAILED` and a non-empty `error` field. Also asserts the run completes cleanly without an exception escaping `graph.invoke()`.

**Important constraints:**
- Routing functions remain pure. No mutation.
- The existing two-gate routing (approval check → iteration check) stays unchanged on the success path.
- `_safe_node` does not catch `KeyboardInterrupt` or `SystemExit` — bare `except Exception` only.

**Acceptance:**
- Existing pipeline test still passes (success path unchanged)
- New failure test passes
- Forced failure in any agent results in `FAILED` status, populated `error`, no traceback
- `ruff check .` clean

**Commit message:** `feat: add failure handling and safe node wrappers to workflow`

---

### Step 6 — Frontend error rendering

Turn `FAILED` state into a useful UI instead of a Streamlit traceback.

**Files:**
- `frontend/components/error_state.py` (new)
- `frontend/pages/workflow.py`
- `frontend/pages/strategy.py`
- `frontend/pages/creative.py`

**Changes:**

1. **New component `error_state.py`.** Takes an `AgencyState` (already rehydrated) and renders:
   - A clear error heading
   - The error message from `state.error`
   - The provider and model that were in use (from `state.llm_provider` / `state.llm_model`, falling back to config defaults if `None`)
   - A short hint: "Try again, or switch provider/model in the sidebar and re-run."
   - Use existing theme styling — match the look of other components, don't introduce new visual primitives.

2. **Workflow page.** After the rehydration step, check `final_state.status == WorkflowStatus.FAILED`. If so, render the error component and skip the normal output rendering. Make sure `st.session_state` cleanup means the next "Run" click works without weirdness — specifically, clear any cached final state before starting a new run.

3. **Strategy and Creative standalone pages.** Same pattern. These pages don't go through the full graph but they do call agent functions directly, so wrap those calls in their own try/except that constructs a minimal `AgencyState` with `status=FAILED` and `error=...` and routes to the error component.

**Acceptance:**
- Forcing a pipeline failure (e.g. by setting an invalid API key temporarily) shows the error component, not a traceback
- The error component shows which provider/model was in use
- After a failed run, clicking "Run" again starts a fresh run cleanly
- All three pages (workflow, strategy, creative) handle failures consistently
- `ruff check .` clean

**Commit message:** `feat: add error state rendering to frontend pages`

---

### Step 7 — ADR 0012

Written **last**, after Steps 2–6 are committed and the system is observed working. ADRs document validated decisions, not speculative ones.

**Files:**
- `docs/adr/0012-error-handling-and-graceful-degradation.md` (new)
- `docs/adr/README.md` (update index)

**Content:**

The ADR should cover, in the project's existing ADR style (Context / Decision / Consequences):

- **Context:** the gap before this work (no retries, tracebacks on transient failures, no failure contract between agents and frontend)
- **Decisions:**
  1. Retry-only fallback policy (no cross-provider, no model fallback). Explain why — provider comparison use case, score calibration drift, artefact coherence.
  2. Two-layer retry model (transport in `get_llm()`, validation in CD). Explain the layer boundary: transport errors are framework-level cross-cutting concerns; schema validation is application-level and needs the schema in scope.
  3. Explicit retryable exception set (not LangChain's default). Loud failures over silent ones.
  4. `FAILED` status and `error` field as the contract between graph and frontend.
  5. Safe-node wrapper at graph-build time (not decorators on agents, not try/except inside agents). Keeps agents clean and makes resilience visible at the orchestration layer.
- **Consequences:** positive (resilience, clean failure UX, framework integration), negative (LangChain coupling deepens, retry policy needs tuning over time, no recovery from mid-run failures), neutral (sets the pattern for future agents — they get retries for free but must respect the failure contract)
- **Non-goals:** explicitly list cross-provider fallback, model fallback, checkpointing, token budgeting, rate limiting — and where each one is deferred to.

Update `docs/adr/README.md` to add row 0012 to the index.

**Commit message:** `docs: add ADR 0012 for error handling and graceful degradation`

---

## Definition of done for Phase 6.1

- All seven steps committed
- Full pipeline test passes
- Forced-failure test passes
- A real failure (e.g. invalid API key) renders cleanly in the frontend on all three pages
- ADR 0012 written and indexed
- `CLAUDE.md` updated if any new conventions were introduced (e.g. "all new agents are wrapped with `_safe_node`")
