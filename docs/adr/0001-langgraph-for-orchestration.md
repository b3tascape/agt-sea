# ADR 0001: LangGraph for Agent Orchestration

**Status:** Accepted  
**Date:** 2026-02-15

## Context

agt_sea requires an orchestration framework to manage a multi-agent workflow with conditional routing and iterative feedback loops. The key requirements are:

- A graph-based execution model where agents are nodes and edges define flow
- Support for conditional branching (Creative Director approval gate)
- Support for cyclical graphs (revision loop back to Creative)
- Shared mutable state passed between nodes
- Human-in-the-loop interrupt/resume capability (future requirement)

Alternatives considered:

- **CrewAI** — higher-level abstraction with role-based agents. Simpler to get started but less control over graph structure and routing logic.
- **AutoGen** — Microsoft's multi-agent framework. Strong on conversational agents but heavier setup and less intuitive for directed graph workflows.
- **Custom orchestration** — building from scratch with plain Python. Maximum control but significant boilerplate for state management, routing, and error handling.

## Decision

Use **LangGraph** as the orchestration framework.

## Consequences

- **Positive:** Explicit graph definition makes the workflow transparent and debuggable. Native support for conditional edges, cycles, and shared state fits the agt_sea architecture directly. Built on LangChain, so it integrates cleanly with the LLM abstraction layer (see ADR 0002). Supports human-in-the-loop patterns for future phases.
- **Negative:** Tighter coupling to the LangChain ecosystem. If LangGraph's API changes significantly, migration effort is required.
- **Negative:** Smaller community than some alternatives, so fewer tutorials and Stack Overflow answers available.
