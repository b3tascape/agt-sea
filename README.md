# 🌊 agt_sea

An experimental AI creative agency framework — three AI agents collaborate to transform a client brief into a creative campaign concept.

A Strategist writes the creative brief, a Creative generates ideas, and a Creative Director evaluates the work through a configurable creative philosophy. The system iterates until the work meets the quality threshold or the iteration budget is exhausted.

Built with LangGraph, LangChain, and Streamlit.

---

## How It Works

```mermaid
graph LR
    A(["`**input:**
    Client brief supplied`"]):::input --> B["`**strategist**
    Creative brief written`"]:::agent

    B --> C["`**creative**
    Idea generation`"]:::agent

    C --> D["`**creative director**
    Evaluation:
    1. Rate creative
    2. Feedback`"]:::agent

    CP(["`**creative_philosophy**`"]):::philosophy --> D

    D --> E{"`**creative
    standard hit?**
    cd_score ≥ 85%`"}:::decision

    E -->|yes| G(["`**output:**
    Approved creative
    direction`"]):::output

    E -->|no| F{"`**max iterations
    reached?**
    iteration ≥ 5`"}:::decision

    F -->|no| C
    F -->|"`yes: output
    top scoring idea`"| G

    classDef input fill:#d3d3d3,color:#000,stroke:#999
    classDef agent fill:#2196F3,color:#fff,stroke:#1976D2
    classDef decision fill:#F5C542,color:#000,stroke:#D4A017
    classDef output fill:#d3d3d3,color:#000,stroke:#999
    classDef philosophy fill:#80deea,color:#000,stroke:#4dd0e1
```

### Agents

| Agent | Role | Output |
|-------|------|--------|
| **Strategist** | Transforms the raw client brief into a focused creative brief | Challenge, audience, insight, proposition, tone |
| **Creative** | Generates three distinct creative approaches per iteration | Concept title, core idea, execution, rationale |
| **Creative Director** | Evaluates creative work through a chosen philosophical lens | Structured score (0–100), strengths, weaknesses, direction |

### Creative Philosophies

The Creative Director's evaluation lens is configurable. Each philosophy shapes what "good" looks like:

| Philosophy | Lens |
|-----------|------|
| Bold & Disruptive | Rewards risk-taking and convention-breaking |
| Minimal & Refined | Values restraint, elegance, and precision |
| Emotionally Driven | Prioritises genuine human emotion and authenticity |
| Data Led | Demands strategic rationale grounded in evidence |
| Culturally Provocative | Rewards cultural participation and relevance |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) |
| LLM Abstraction | [LangChain](https://github.com/langchain-ai/langchain) |
| Data Models | [Pydantic](https://docs.pydantic.dev/) |
| Frontend | [Streamlit](https://streamlit.io/) |
| Package Management | [uv](https://github.com/astral-sh/uv) |

### LLM Provider Support

The framework supports provider switching via configuration — change the `LLM_PROVIDER` environment variable to swap between:

- **Anthropic** (Claude) — default
- **Google** (Gemini)
- **OpenAI** (GPT)

---

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- An API key for at least one supported LLM provider

### Installation

```bash
# Clone the repo
git clone https://github.com/b3tascape/agt-sea.git
cd agt-sea

# Install dependencies
uv sync
uv pip install -e .

# Set up environment variables
cp .env.example .env
# Edit .env and add your API key(s)
```

### Run the Frontend

```bash
uv run streamlit run frontend/app.py
```

### Run the Pipeline from Terminal

```bash
uv run python tests/test_pipeline.py
```

---

## Project Structure

```
agt_sea/
├── docs/
│   ├── architecture.md              # Architecture diagram
│   └── adr/                         # Architecture Decision Records
├── src/
│   └── agt_sea/
│       ├── agents/
│       │   ├── strategist.py        # Brief → creative brief
│       │   ├── creative.py          # Creative brief → concepts
│       │   └── creative_director.py # Concepts → evaluation
│       ├── graph/
│       │   └── workflow.py          # LangGraph orchestration
│       ├── llm/
│       │   └── provider.py          # LLM provider abstraction
│       ├── models/
│       │   └── state.py             # Pydantic data models
│       └── config.py                # Configuration & defaults
├── tests/
│   ├── test_strategist.py           # Strategist isolation test
│   ├── test_creative.py             # Strategist → Creative test
│   └── test_pipeline.py             # Full pipeline test
├── frontend/
│   └── app.py                       # Streamlit interface
├── briefs/
│   └── sample_brief_001.txt         # Sample client brief
├── pyproject.toml
├── .env.example
└── README.md
```

---

## Architecture Decisions

Key technical decisions are documented as Architecture Decision Records in [`docs/adr/`](docs/adr/):

- **ADR 0001** — LangGraph for orchestration
- **ADR 0002** — LangChain for LLM provider switching
- **ADR 0003** — Pydantic for state and data modelling
- **ADR 0004** — Structured output for CD evaluation
- **ADR 0005** — Streamlit for frontend
- **ADR 0006** — Iterative creative loop with bounded execution

---

## Status

🟢 **MVP functional** — the core pipeline runs end-to-end with live progress in the Streamlit frontend. Currently in active development.

### Roadmap

- [ ] Frontend refinement and UX polish
- [ ] Human-in-the-loop approval points
- [ ] Structured logging and tracing (LangSmith)
- [ ] Error handling and graceful degradation
- [ ] RAG-enhanced creative philosophies
- [ ] Provider comparison tooling

---

## License

This project is an experimental learning and portfolio piece. See [LICENSE](LICENSE) for details.
