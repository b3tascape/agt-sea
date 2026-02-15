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

    CP(["`**creative_philosophy**
    _text / md — can be enhanced
    via RAG documentation_`"]):::philosophy --> D

    D --> E{"`**creative
    standard hit?**
    cd_score ≥ 80%`"}:::decision

    E -->|yes| G(["`**output:**
    Proposed creative
    direction`"]):::output

    E -->|no| F{"`**max iterations
    reached?**
    iteration ≥ max(5)`"}:::decision

    F -->|no| C
    F -->|"`yes: output
    top scoring idea`"| G

    classDef input fill:#d3d3d3,color:#000,stroke:#999
    classDef agent fill:#2196F3,color:#fff,stroke:#1976D2
    classDef decision fill:#F5C542,color:#000,stroke:#D4A017
    classDef output fill:#d3d3d3,color:#000,stroke:#999
    classDef philosophy fill:#80deea,color:#000,stroke:#4dd0e1