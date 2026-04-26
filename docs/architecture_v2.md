graph TD
    A(["`**input:**
    Client brief supplied`"]):::input --> B["`**strategist**
    Creative brief written`"]:::agent

    SP(["`**strat_philosophy**`"]):::philosophy --> B

    B --> C1["`**creative 1**
    Core idea generation
    1–2 sentence articulations`"]:::agent

    CP1(["`**creative_philosophy
    provenance · taste**
    _temperature_`"]):::philosophy --> C1

    C1 --> T1(["`territory 1`"]):::territory
    C1 --> T2(["`territory 2`"]):::territory
    C1 --> T3(["`territory 3`"]):::territory

    T1 --> H{"`**user select
    preference**`"}:::human
    T2 --> H
    T3 --> H

    H -->|"`rerun with
    optional context`"| C1

    H -->|"`preference
    selected`"| C2["`**creative 2**
    Campaign generation`"]:::agent

    CP2(["`**creative_philosophy
    provenance · taste**
    _temperature_`"]):::philosophy --> C2

    C2 --> GR["`**CD grader**
    Score + rationale
    _temp = 0_`"]:::grader

    GR --> E{"`**80% hit?**`"}:::decision

    E -->|yes| SYN["`**creative director**
    Synthesise, judge,
    recommend`"]:::agent

    E -->|no| F{"`**max iter?**`"}:::decision

    F -->|no| FB["`**CD feedback**
    Revision direction`"]:::agent

    FB --> C2

    F -->|"`yes: output
    best scoring`"| SYN

    CPCD(["`**creative_philosophy
    provenance · taste**
    _temperature_`"]):::philosophy --> SYN

    SYN --> G(["`**output:**
    Proposed creative
    direction`"]):::output

    classDef input fill:#d3d3d3,color:#000,stroke:#999
    classDef agent fill:#2196F3,color:#fff,stroke:#1976D2
    classDef decision fill:#F5C542,color:#000,stroke:#D4A017
    classDef output fill:#d3d3d3,color:#000,stroke:#999
    classDef philosophy fill:#71F7B7,color:#000,stroke:#4dd0e1
    classDef territory fill:#E8DEF8,color:#000,stroke:#7F67BE
    classDef human fill:#FF9800,color:#fff,stroke:#F57C00
    classDef grader fill:#B0BEC5,color:#000,stroke:#78909C
