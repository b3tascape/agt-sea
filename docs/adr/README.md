# Architecture Decision Records

This directory contains the Architecture Decision Records (ADRs) for agt_sea. Each ADR documents a significant technical decision, its context, and its consequences.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-langgraph-for-orchestration.md) | LangGraph for Agent Orchestration | Accepted |
| [0002](0002-langchain-llm-abstraction.md) | LangChain Chat Models for LLM Provider Switching | Accepted |
| [0003](0003-pydantic-state-modelling.md) | Pydantic for State and Data Modelling | Accepted (boundary handling refined by 0011) |
| [0004](0004-structured-output-cd-evaluation.md) | Structured Output for CD Evaluation | Accepted |
| [0005](0005-streamlit-frontend.md) | Streamlit for Frontend Interface | Accepted |
| [0006](0006-iterative-loop-design.md) | Iterative Creative Loop with Bounded Execution | Accepted (thresholds superseded by 0007) |
| [0007](0007-revised-loop-thresholds.md) | Revised Creative Loop Thresholds | Accepted |
| [0008](0008-multipage-frontend.md) | Multipage Frontend Architecture | Accepted (backfilled) |
| [0009](0009-llm-override-mechanism.md) | LLM Provider and Model Override Mechanism | Accepted (backfilled) |
| [0010](0010-prompt-injection-pattern.md) | Filesystem-Backed Prompt Injection Pattern | Accepted |
| [0011](0011-rehydrate-at-boundary.md) | Rehydrate LangGraph Output to Pydantic at the Boundary | Accepted |
| [0012](0012-error-handling-and-graceful-degradation.md) | Error Handling and Graceful Degradation | Accepted |
| [0013](0013-demo-abuse-mitigation.md) | Demo Abuse Mitigation via Per-Session Run Counter | Accepted |
| [0014](0014-multi-stage-creative-pipeline.md) | Multi-Stage Creative Pipeline with Territory Selection | Accepted |