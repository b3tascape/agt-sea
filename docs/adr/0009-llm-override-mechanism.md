# ADR 0009: LLM Provider and Model Override Mechanism

**Status:** Accepted (backfilled)
**Date:** 2026-04-07

## Context

The original LLM configuration was global and read once at startup from environment variables (`LLM_PROVIDER`, `ANTHROPIC_MODEL`, etc.) via `config.py`. Agents called `get_llm()` which resolved provider and model from config.

This worked for a single-user, single-config deployment but broke down once the frontend introduced sidebar selectors for provider and model. Users expected to switch provider mid-session — for example, comparing how Anthropic and Google handle the same brief — without restarting the app or editing environment variables.

The challenge: agents need to know which provider and model to use *per-run*, not per-process. The frontend needed a way to inject user choices into agent invocations without mutating global state, and without forcing every agent function signature to grow new parameters.

Alternatives considered:

- **Global mutation.** Sidebar writes to a module-level variable in `config.py` that agents read. Simple but breaks if multiple users share a process (Streamlit Cloud), and makes per-run overrides indistinguishable from default config. Mutating config at runtime is also a smell.
- **Threadlocal storage.** Sidebar writes to a `threading.local()` that agents read. Works for per-request isolation but adds machinery for a problem that doesn't really need it in Streamlit's execution model.
- **Function parameters all the way down.** Pass `provider` and `model` explicitly through every agent and graph node. Verbose and noisy — every signature grows two parameters that most code doesn't care about.
- **Optional fields on `AgencyState`.** Add `llm_provider` and `llm_model` as nullable fields on the shared state object. Agents resolve them via a fallback pattern: `state.llm_provider or get_llm_provider()`. State is already the canonical thing flowing through the graph, so this rides on existing infrastructure.

## Decision

Add `llm_provider: LLMProvider | None` and `llm_model: str | None` as optional fields on `AgencyState`. Default both to `None`, meaning "use the config default."

In every agent, resolve provider and model with the same idiom:

```python
provider = state.llm_provider or get_llm_provider()
model = state.llm_model or get_model_name(provider)
llm = get_llm(provider=provider, model=model)
```

`get_llm()` accepts optional `provider` and `model` parameters. When passed, they override the config defaults. When omitted, `get_llm()` falls back to reading from config. This means existing code that doesn't care about overrides keeps working unchanged.

The frontend writes user selections from the sidebar into `st.session_state.llm_provider` and `st.session_state.llm_model`, then passes them into `AgencyState` at construction time:

```python
state = AgencyState(
    client_brief=brief_text,
    llm_provider=st.session_state.llm_provider,
    llm_model=st.session_state.llm_model,
    ...
)
```

From there, the state object flows through the graph as normal, and every agent picks up the overrides via the resolution idiom.

## Consequences

- **Positive:** Per-run overrides without global state mutation. Two users running the app in the same process can use different providers without interfering with each other.
- **Positive:** Backwards compatible. Code that doesn't pass overrides (existing tests, the default `AgencyState()` constructor) continues to work — it falls through to config defaults.
- **Positive:** The override mechanism rides on existing infrastructure. `AgencyState` already flows through every node, so no new plumbing is required.
- **Positive:** The fallback idiom is explicit. Anyone reading `state.llm_provider or get_llm_provider()` immediately understands what's happening — there's no hidden indirection.
- **Positive:** Per-provider model defaults (`ANTHROPIC_MODEL`, `GOOGLE_MODEL`, `OPENAI_MODEL`) still work for cost control on Streamlit Cloud, because the sidebar selector populates from `get_model_name(provider)` and the user can either accept it or pick a different model.
- **Negative:** Two fields on `AgencyState` that exist purely for override purposes, which slightly muddies the data model — they're not really part of the agency's state, they're configuration. Acceptable tradeoff for the simplicity of the resolution pattern.
- **Negative:** Every new agent must remember to use the resolution idiom. Easy to forget and accidentally hardcode `get_llm()` with no arguments, which would silently ignore user overrides. Mitigated by documenting the pattern in CLAUDE.md's Agent Conventions section.
- **Negative:** Temperature and other LLM parameters are not yet covered by this mechanism — only provider and model. If per-run temperature control becomes a requirement, the same pattern can extend to it.
