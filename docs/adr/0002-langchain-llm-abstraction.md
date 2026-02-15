# ADR 0002: LangChain Chat Models for LLM Provider Switching

**Status:** Accepted  
**Date:** 2026-02-15

## Context

agt_sea must support multiple LLM providers (Anthropic, Google, OpenAI) with the ability to switch between them via configuration. This requires a common interface that normalises differences in API signatures, authentication, and response formats.

Alternatives considered:

- **LiteLLM** — a lightweight proxy that unifies LLM APIs behind an OpenAI-compatible interface. Simple but adds an external dependency and another abstraction layer on top of LangGraph.
- **Direct SDK calls** — using each provider's SDK directly with a custom adapter pattern. Maximum control but significant boilerplate to maintain parity across providers.
- **LangChain chat models** — `ChatAnthropic`, `ChatGoogleGenerativeAI`, `ChatOpenAI` share a common `BaseChatModel` interface including `invoke()`, `stream()`, and `with_structured_output()`.

## Decision

Use **LangChain's chat model classes** as the LLM abstraction layer, selected via environment configuration.

## Consequences

- **Positive:** Consistent interface across providers with no custom adapter code. `with_structured_output()` works uniformly, which is critical for the CD evaluation flow (see ADR 0004).
- **Positive:** Native integration with LangGraph — chat models slot directly into graph nodes without translation.
- **Positive:** Provider switching is a single config change rather than a code change.
- **Negative:** Dependency on LangChain's update cycle. When providers ship new features, there may be a lag before LangChain supports them.
- **Negative:** Adds LangChain as a core dependency even for simple LLM calls where direct SDK usage would suffice.
