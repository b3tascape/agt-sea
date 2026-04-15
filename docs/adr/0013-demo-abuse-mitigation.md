# ADR 0013: Demo Abuse Mitigation via Per-Session Run Counter

**Status:** Accepted
**Date:** 2026-04-15

## Context

The live demo at `agt-sea.streamlit.app` is linked from the public README. Every agent run costs real money on real API keys. Three threats to token spend exist at the project's current scale:

1. **Casual spamming** — a single user clicking "Run" repeatedly, whether out of impatience, curiosity, or because they forgot a previous run was already in flight. Likely, cheap to stop, and the most common failure mode for a personal-project demo.
2. **Public abuse** — someone who finds the demo and decides to burn through the API budget on purpose. Less likely but harder to bound because it crosses sessions.
3. **Runaway loops** — already handled. `max_iterations` caps the Creative → CD loop at 3 passes per run (ADR 0007), so a single run has a fixed cost ceiling regardless of what the agents do.

Provider spend caps — set in Phase 6.1 Step 1 on each of the Anthropic, Google, and OpenAI dashboards — are the hard ceiling for threats 1 and 2. They don't stop abuse, they just stop it from becoming catastrophic. When a cap fires, the API key gets disabled and the demo goes dark until manually reset. That's acceptable as a backstop but miserable as a first line of defence: a single enthusiastic user could trip the cap, take the demo offline, and force a reset before the next person even arrives.

This ADR addresses the gap between "no protection at all" and "spend cap hit, API key disabled." The goal is a speed bump that makes the common case (casual spamming) cheap to stop, without pretending to solve the harder case (determined abuse) which is a product decision, not an engineering one.

Alternatives considered:

- **Per-IP rate limiting.** The right answer in principle, but wrong for current scale. Streamlit Cloud sits behind a proxy, so `request.remote_ip` isn't trustworthy without header parsing, and the parsing depends on the specific proxy configuration. Doing it properly means either a sidecar (Upstash, Redis) or a Cloudflare rule in front of the app — both introduce infrastructure and dependencies for a personal project that doesn't yet justify them.
- **Auth wall.** Login, accounts, per-user quotas. The right answer when the project graduates past portfolio status, but it changes the product shape — the demo stops being a demo. Out of scope here.
- **Token budget per session.** Track cumulative token consumption and block when the session exceeds a budget. More accurate than a run counter (one expensive run with three iterations costs more than one cheap run with one), but requires instrumenting every LLM call and hooking into LangChain's usage metadata. Observability work that belongs in Phase 6.4, not Phase 6.1b.
- **Circuit breakers around the LLM provider.** Trip on failure rate, not on user behaviour. Wrong threat model — circuit breakers protect against provider outages, not against users spamming a working provider.
- **Per-session run counter (chosen).** Trivial, self-contained, no new dependencies, no infrastructure. Solves the common case at the cost of a refresh button being a trivial bypass for the uncommon case. Honest about what it is.

## Decision

A per-session run counter enforced by a single gate function, `check_run_allowed()`, that every agent-invoking page calls before constructing `AgencyState` or invoking an agent.

- **State.** `st.session_state.run_count`, initialised to `0` in `frontend/app.py`'s existing `setdefault` block alongside the other session defaults.
- **Cap.** `DEMO_RUN_CAP` in `config.py`, default `10`, overridable via env var or Streamlit secret through `_get_secret()`. Cast to `int` so the override surface is consistent with `MAX_ITERATIONS` and `APPROVAL_THRESHOLD`.
- **Gate.** `frontend/components/run_guard.py` exposes `check_run_allowed() -> bool` and `render_run_limit_reached() -> None`. `check_run_allowed()` both reads and increments the counter in one call — the check and the bump are atomic from the caller's perspective, so there is no way to check the counter and then forget to increment it. The pure logic lives in a module-private `_check_and_increment(state, cap)` helper that operates on any mutable mapping, so unit tests can exercise it without a Streamlit session.
- **Scope.** Single shared counter across all agent-invoking pages (`workflow`, `strategy`, `creative`, and eventually `tools`). One run = one increment regardless of how many LLM calls the run makes internally. A workflow run with three creative iterations and one CD evaluation still counts as one run. This is deliberate — the counter measures user-initiated work, not underlying token cost.
- **Reset semantics.** Refresh-to-reset only. No time-based reset, no persistent storage, no database. Streamlit's session state is already bound to the browser tab lifecycle; leaning on that is the simplest possible implementation.
- **Caller pattern.**
  ```python
  if not check_run_allowed():
      render_run_limit_reached()
      st.stop()
  # ... proceed with agent call
  ```
  `st.stop()` halts the script after rendering the limit message. This is the idiomatic Streamlit early-exit pattern and avoids any `if/else` nesting around the agent invocation.
- **Tools page.** Currently a holding message with no run handler. The guard is not wired in yet, but a `TODO` comment marks the location for when tool agents land.

## Consequences

- **Positive:** Stops casual spamming with ~60 lines of code, zero new dependencies, and zero infrastructure. The common failure mode of the demo is now bounded.
- **Positive:** Fully configurable via `DEMO_RUN_CAP`. Setting it to `0` disables the demo entirely (useful kill switch if the provider cap is close to tripping). Setting it to `999` effectively disables the limit for local development.
- **Positive:** One shared gate across all agent-invoking pages. A future agent-invoking page only needs to add three lines (`if not check_run_allowed(): render_run_limit_reached(); st.stop()`) to inherit the protection — no new per-page counters, no drift.
- **Positive:** The check-and-increment is atomic in the gate function, so a caller cannot accidentally check the counter and forget to increment it. The failure mode where the gate passes but the counter never bumps is structurally impossible.
- **Positive:** Pure logic is extracted into `_check_and_increment(state, cap)`, which takes a mutable mapping and the cap as explicit parameters. Unit tests in `tests/test_run_guard.py` exercise it directly with plain dicts and never import Streamlit. Convention established here: any Streamlit-coupled logic that has non-trivial behaviour should be factored this way.
- **Negative:** Trivially bypassable. A refresh, an incognito window, or a different browser all reset the counter. This is the intended behaviour — the counter is a speed bump, not a wall — but it does mean the ADR cannot claim to stop a determined user. The real ceiling for that case is the provider spend caps.
- **Negative:** Session state resets on refresh, so the counter also resets. A determined user can spam indefinitely by refreshing between runs, at the cost of losing their session state (brief input, prior results) each time. Accepted.
- **Negative:** No feedback before the cap is hit. A user on run 9 has no warning that they are one click away from being stopped. A future refinement could render a "runs remaining: N" hint in the sidebar, but it was left out of this workstream to keep the scope tight.
- **Neutral:** When the project moves past portfolio / demo status, the real answer is an auth wall or API key gating — a product decision that supersedes this counter entirely. The counter is not designed to scale into a permanent solution. It is designed to hold the line until the project stops being a demo.
- **Neutral:** The pattern does nothing for non-agent-invoking pages (e.g. pages that just read cached results). This is correct — the counter guards the thing that costs money, which is the LLM call, not the render.

## Non-goals

These are explicitly out of scope for Phase 6.1b and remain so. They are not rejected — they are deferred, each with a specific home.

- **Per-IP rate limiting.** Streamlit Cloud proxy header issues, Cloudflare / Upstash complexity, premature for current scale. The right answer when the project outgrows Streamlit Cloud's free tier.
- **Auth wall.** Changes product shape. Separate decision when the project moves off portfolio status.
- **Token budgets per session.** An observability concern that belongs in Phase 6.4 (structured logging / tracing). Requires instrumenting LLM calls, which is Phase 6.4's job anyway.
- **Circuit breakers.** Premature for current scale and wrong threat model — circuit breakers protect against provider outages, not user spamming.
- **Time-based reset (e.g. "10 runs per hour").** Would require either persistent storage or wall-clock tracking across sessions. Refresh-to-reset is simpler, self-contained, and adequate for the threat model.
- **Sidebar "runs remaining" indicator.** Out of scope to keep the workstream tight. Trivial to add later if the UX gap proves noticeable.
