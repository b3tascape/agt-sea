"""
agt_sea — Streamlit Frontend (Retro DOS Theme)

Run with: uv run streamlit run frontend/app.py
"""

import sys
from pathlib import Path

import streamlit as st

# Ensure agt_sea package is importable (needed for Streamlit Cloud)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agt_sea.graph.workflow import build_graph
from agt_sea.models.state import (
    AgencyState,
    AgentRole,
    CreativePhilosophy,
    WorkflowStatus,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="agt_sea",
    page_icon="🌊",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Retro DOS Theme — Custom CSS
# ---------------------------------------------------------------------------

RETRO_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap');

    /* --- Root variables — EGA/VGA palette --- */
    :root {
        --dos-black: #0a0a14;
        --dos-dark-blue: #0f0f2e;
        --dos-blue: #2424c4;
        --dos-cyan: #00e5ff;
        --dos-magenta: #e040fb;
        --dos-purple: #9c27b0;
        --dos-red: #e53935;
        --dos-yellow: #ffd600;
        --dos-green: #00e676;
        --dos-white: #e0e0e0;
        --dos-grey: #808080;
        --dos-orange: #ff6d00;
        --pixel-font: 'Press Start 2P', monospace;
        --terminal-font: 'VT323', monospace;
    }

    /* --- Global background --- */
    .stApp {
        background: linear-gradient(180deg, #0a0a14 0%, #0f0f2e 50%, #1a0a2e 100%) !important;
        background-attachment: fixed !important;
    }

    /* --- Scanline overlay --- */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: repeating-linear-gradient(
            0deg,
            rgba(0, 0, 0, 0.15) 0px,
            rgba(0, 0, 0, 0.15) 1px,
            transparent 1px,
            transparent 3px
        );
        pointer-events: none;
        z-index: 999;
    }

    /* --- Sidebar --- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0f2e 0%, #1a0a2e 100%) !important;
        border-right: 3px solid var(--dos-cyan) !important;
    }

    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li {
        font-family: var(--terminal-font) !important;
        font-size: 18px !important;
        color: var(--dos-white) !important;
        line-height: 1.6 !important;
    }

    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stMarkdown strong {
        font-family: var(--pixel-font) !important;
        font-size: 10px !important;
        color: var(--dos-yellow) !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* --- Sidebar title --- */
    section[data-testid="stSidebar"] h1 {
        font-family: var(--pixel-font) !important;
        font-size: 18px !important;
        color: var(--dos-cyan) !important;
        text-shadow: 2px 2px 0px var(--dos-blue), 4px 4px 0px rgba(0,0,0,0.5);
        padding-bottom: 8px;
        border-bottom: 2px dashed var(--dos-purple);
    }

    /* --- Horizontal rules --- */
    section[data-testid="stSidebar"] hr {
        border-color: var(--dos-purple) !important;
        border-style: dashed !important;
    }

    hr {
        border-color: var(--dos-blue) !important;
        border-style: dashed !important;
    }

    /* --- Main title --- */
    .stApp h1 {
        font-family: var(--pixel-font) !important;
        font-size: 28px !important;
        color: var(--dos-cyan) !important;
        text-shadow:
            3px 3px 0px var(--dos-blue),
            6px 6px 0px rgba(0,0,0,0.4);
        letter-spacing: 2px;
        padding-bottom: 10px;
    }

    /* --- Subheaders --- */
    .stApp h3 {
        font-family: var(--pixel-font) !important;
        font-size: 13px !important;
        color: var(--dos-yellow) !important;
        text-shadow: 2px 2px 0px rgba(0,0,0,0.5);
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* --- Body text --- */
    .stApp .stMarkdown p,
    .stApp .stMarkdown li {
        font-family: var(--terminal-font) !important;
        font-size: 20px !important;
        color: var(--dos-white) !important;
        line-height: 1.5 !important;
    }

    /* --- Text area --- */
    .stTextArea textarea {
        font-family: var(--terminal-font) !important;
        font-size: 20px !important;
        color: var(--dos-green) !important;
        background-color: #0a0a14 !important;
        border: 2px solid var(--dos-blue) !important;
        border-radius: 0px !important;
        caret-color: var(--dos-green) !important;
    }

    .stTextArea textarea:focus {
        border-color: var(--dos-cyan) !important;
        box-shadow: 0 0 10px rgba(0, 229, 255, 0.3) !important;
    }

    .stTextArea textarea::placeholder {
        color: var(--dos-grey) !important;
        font-family: var(--terminal-font) !important;
    }

    .stTextArea label {
        font-family: var(--pixel-font) !important;
        font-size: 10px !important;
        color: var(--dos-yellow) !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* --- Primary button --- */
    .stButton > button[kind="primary"],
    .stButton > button {
        font-family: var(--pixel-font) !important;
        font-size: 12px !important;
        color: var(--dos-black) !important;
        background: linear-gradient(180deg, var(--dos-yellow) 0%, var(--dos-orange) 100%) !important;
        border: 3px solid var(--dos-yellow) !important;
        border-radius: 0px !important;
        padding: 12px 24px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.1s ease !important;
        box-shadow: 4px 4px 0px rgba(0,0,0,0.5) !important;
    }

    .stButton > button:hover {
        background: linear-gradient(180deg, var(--dos-cyan) 0%, var(--dos-blue) 100%) !important;
        border-color: var(--dos-cyan) !important;
        color: var(--dos-white) !important;
        transform: translate(2px, 2px) !important;
        box-shadow: 2px 2px 0px rgba(0,0,0,0.5) !important;
    }

    .stButton > button:active {
        transform: translate(4px, 4px) !important;
        box-shadow: none !important;
    }

    /* --- Select box --- */
    .stSelectbox > div > div {
        font-family: var(--terminal-font) !important;
        font-size: 18px !important;
        background-color: #0a0a14 !important;
        color: var(--dos-cyan) !important;
        border: 2px solid var(--dos-blue) !important;
        border-radius: 0px !important;
    }

    /* --- Expander --- */
    .streamlit-expanderHeader {
        font-family: var(--pixel-font) !important;
        font-size: 11px !important;
        color: var(--dos-cyan) !important;
        background-color: rgba(15, 15, 46, 0.8) !important;
        border: 2px solid var(--dos-blue) !important;
        border-radius: 0px !important;
    }

    .streamlit-expanderContent {
        background-color: rgba(10, 10, 20, 0.9) !important;
        border: 2px solid var(--dos-blue) !important;
        border-top: none !important;
        border-radius: 0px !important;
    }

    details {
        border: 2px solid var(--dos-blue) !important;
        border-radius: 0px !important;
        background-color: rgba(10, 10, 20, 0.9) !important;
    }

    details summary {
        font-family: var(--pixel-font) !important;
        font-size: 11px !important;
        color: var(--dos-cyan) !important;
    }

    /* --- Status containers --- */
    [data-testid="stStatusWidget"] {
        background-color: rgba(10, 10, 20, 0.9) !important;
        border: 2px solid var(--dos-blue) !important;
        border-radius: 0px !important;
    }

    /* --- Metrics --- */
    [data-testid="stMetric"] {
        background-color: rgba(15, 15, 46, 0.6) !important;
        border: 2px solid var(--dos-blue) !important;
        border-radius: 0px !important;
        padding: 12px !important;
    }

    [data-testid="stMetricLabel"] {
        font-family: var(--pixel-font) !important;
        font-size: 9px !important;
        color: var(--dos-yellow) !important;
        text-transform: uppercase;
    }

    [data-testid="stMetricValue"] {
        font-family: var(--pixel-font) !important;
        font-size: 16px !important;
        color: var(--dos-cyan) !important;
    }

    /* --- Success / Warning banners --- */
    .stSuccess {
        font-family: var(--pixel-font) !important;
        background-color: rgba(0, 230, 118, 0.1) !important;
        border: 2px solid var(--dos-green) !important;
        border-radius: 0px !important;
        color: var(--dos-green) !important;
    }

    .stWarning {
        font-family: var(--pixel-font) !important;
        background-color: rgba(255, 214, 0, 0.1) !important;
        border: 2px solid var(--dos-yellow) !important;
        border-radius: 0px !important;
        color: var(--dos-yellow) !important;
    }

    [data-testid="stAlert"] {
        border-radius: 0px !important;
        font-family: var(--terminal-font) !important;
        font-size: 20px !important;
    }

    /* --- Columns text --- */
    .stColumn .stMarkdown strong {
        font-family: var(--pixel-font) !important;
        font-size: 9px !important;
        color: var(--dos-yellow) !important;
    }

    /* --- Blinking cursor effect for title --- */
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0; }
    }

    /* --- Star twinkle animation --- */
    @keyframes twinkle {
        0%, 100% { opacity: 0.3; }
        50% { opacity: 1; }
    }

    /* --- Tooltip / help text --- */
    .stTooltipIcon {
        color: var(--dos-purple) !important;
    }
</style>
"""

st.markdown(RETRO_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Starfield header decoration
# ---------------------------------------------------------------------------

STARFIELD_HTML = """
<div style="
    position: relative;
    width: 100%;
    height: 8px;
    margin-bottom: 20px;
    background: transparent;
    overflow: hidden;
">
    <div style="
        position: absolute;
        width: 3px; height: 3px;
        background: #00e5ff;
        border-radius: 50%;
        top: 2px; left: 5%;
        box-shadow:
            0 0 4px #00e5ff,
            100px 3px 0 #ffd600,
            250px -1px 0 #e040fb,
            400px 2px 0 #00e676,
            550px 0px 0 #00e5ff,
            700px 3px 0 #ffd600,
            850px -1px 0 #e040fb;
        animation: twinkle 3s ease-in-out infinite;
    "></div>
</div>
"""

# ---------------------------------------------------------------------------
# Sidebar — inputs
# ---------------------------------------------------------------------------

st.sidebar.markdown("# agt_sea")
st.sidebar.markdown(STARFIELD_HTML, unsafe_allow_html=True)
st.sidebar.markdown("*An AI creative agency framework*")
st.sidebar.markdown("---")

# Creative philosophy selector
philosophy_labels = {
    CreativePhilosophy.BOLD_AND_DISRUPTIVE: ">> Bold & Disruptive",
    CreativePhilosophy.MINIMAL_AND_REFINED: ">> Minimal & Refined",
    CreativePhilosophy.EMOTIONALLY_DRIVEN: ">> Emotionally Driven",
    CreativePhilosophy.DATA_LED: ">> Data Led",
    CreativePhilosophy.CULTURALLY_PROVOCATIVE: ">> Culturally Provocative",
}

selected_philosophy = st.sidebar.selectbox(
    "Creative Philosophy",
    options=list(philosophy_labels.keys()),
    format_func=lambda x: philosophy_labels[x],
    help="Sets the Creative Director's evaluation lens.",
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**How it works:**"
)
st.sidebar.markdown(
    "Submit a client brief and watch three AI agents "
    "collaborate — a `STRATEGIST` writes the creative brief, a `CREATIVE` "
    "generates ideas, and a `CREATIVE DIRECTOR` evaluates the work."
)

st.sidebar.markdown(STARFIELD_HTML, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Main area — brief input
# ---------------------------------------------------------------------------

st.markdown(STARFIELD_HTML, unsafe_allow_html=True)
st.title("🌊 agt_sea")
st.markdown("### > Submit your client brief_")

brief_text = st.text_area(
    "Client Brief",
    height=200,
    placeholder=(
        "> Describe your brand, target audience, campaign objectives, "
        "channels, budget, and timeline..."
    ),
)

run_button = st.button(
    "▶ Run Creative Pipeline",
    type="primary",
    disabled=not brief_text,
)

# ---------------------------------------------------------------------------
# Pipeline execution with live progress
# ---------------------------------------------------------------------------

if run_button and brief_text:
    # Build a fresh graph for each run
    graph = build_graph()

    initial_state = AgencyState(
        client_brief=brief_text,
        creative_philosophy=selected_philosophy,
    )

    # Progress tracking
    progress_container = st.container()
    results_container = st.container()

    with progress_container:
        st.markdown("---")
        st.markdown("### > Pipeline executing..._")

        # Stream through the graph node by node
        final_state = None
        node_labels = {
            "strategist": ("📋 STRATEGIST", "Writing creative brief..."),
            "creative": ("💡 CREATIVE", "Generating ideas..."),
            "creative_director": ("🎯 CREATIVE DIRECTOR", "Evaluating work..."),
            "check_iterations": ("🔄 ITERATION CHECK", "Checking iteration limit..."),
            "finalise_approved": ("✅ APPROVED", "Creative work approved!"),
            "finalise_max_iterations": ("⚠️ MAX ITERATIONS", "Selecting best work..."),
        }

        for event in graph.stream(initial_state):
            # Each event is a dict with the node name as key
            for node_name, node_output in event.items():
                label, description = node_labels.get(
                    node_name, (node_name, "Processing...")
                )

                with st.status(f"{label}", expanded=False) as status:
                    st.write(description)

                    if node_name == "strategist":
                        st.markdown("**Creative Brief (preview):**")
                        st.markdown(node_output.get("creative_brief", "")[:500] + "...")
                        status.update(label=f"{label} ✓", state="complete")

                    elif node_name == "creative":
                        iteration = node_output.get("iteration", 0)
                        st.markdown(f"**Iteration {iteration} — Concepts (preview):**")
                        st.markdown(node_output.get("creative_concept", "")[:500] + "...")
                        status.update(
                            label=f"{label} [ITER {iteration}] ✓",
                            state="complete",
                        )

                    elif node_name == "creative_director":
                        evaluation = node_output.get("cd_evaluation")
                        if evaluation:
                            st.metric("Score", f"{evaluation.score}/100")
                            st.markdown(f"**Direction:** {evaluation.direction}")
                        status.update(label=f"{label} ✓", state="complete")

                    elif node_name in ("finalise_approved", "finalise_max_iterations"):
                        status.update(label=f"{label}", state="complete")

                    else:
                        status.update(label=f"{label} ✓", state="complete")

                # Keep track of the latest state
                final_state = node_output

    # ---------------------------------------------------------------------------
    # Results — expandable history and final output
    # ---------------------------------------------------------------------------

    if final_state:
        with results_container:
            st.markdown("---")

            # Final output
            status = final_state.get("status")
            if status == WorkflowStatus.APPROVED:
                st.success("✅ CREATIVE WORK APPROVED")
            elif status == WorkflowStatus.MAX_ITERATIONS_REACHED:
                st.warning("⚠️ MAX ITERATIONS REACHED — SHOWING BEST SCORING IDEA")

            st.markdown("### > Final creative concept_")
            st.markdown(final_state.get("creative_concept", ""))

            # Pipeline history
            st.markdown("---")
            st.markdown("### > Pipeline history_")

            history = final_state.get("history", [])
            iteration = 0

            for entry in history:
                if entry.agent == AgentRole.STRATEGIST:
                    with st.expander("📋 STRATEGIST — Creative Brief"):
                        col1, col2, col3 = st.columns(3)
                        col1.markdown(f"**Provider:** {entry.provider.value}")
                        col2.markdown(f"**Model:** {entry.model}")
                        col3.markdown(
                            f"**Date:** {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        st.markdown("---")
                        st.markdown(entry.content)

                elif entry.agent == AgentRole.CREATIVE:
                    iteration += 1
                    with st.expander(
                        f"💡 CREATIVE — Iteration {iteration}"
                    ):
                        col1, col2, col3 = st.columns(3)
                        col1.markdown(f"**Provider:** {entry.provider.value}")
                        col2.markdown(f"**Model:** {entry.model}")
                        col3.markdown(
                            f"**Date:** {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        st.markdown("---")
                        st.markdown(entry.content)

                elif entry.agent == AgentRole.CREATIVE_DIRECTOR:
                    with st.expander(
                        f"🎯 CREATIVE DIRECTOR — Iteration {iteration} "
                        f"[SCORE: {entry.evaluation.score}/100]"
                    ):
                        col1, col2, col3 = st.columns(3)
                        col1.markdown(f"**Provider:** {entry.provider.value}")
                        col2.markdown(f"**Model:** {entry.model}")
                        col3.markdown(
                            f"**Date:** {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        st.markdown("---")

                        score_col, detail_col = st.columns([1, 3])
                        with score_col:
                            st.metric("Score", f"{entry.evaluation.score}/100")
                        with detail_col:
                            st.markdown("**Strengths:**")
                            for s in entry.evaluation.strengths:
                                st.markdown(f"- {s}")
                            st.markdown("**Weaknesses:**")
                            for w in entry.evaluation.weaknesses:
                                st.markdown(f"- {w}")

                        st.markdown(f"**Direction:** {entry.evaluation.direction}")

            # Run metadata
            st.markdown("---")
            st.markdown("### > Run metadata_")
            meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
            meta_col1.metric("Iterations", final_state.get("iteration", 0))
            meta_col2.metric("History", len(history))
            meta_col3.metric(
                "Philosophy",
                philosophy_labels.get(selected_philosophy, "").replace(">> ", ""),
            )
            meta_col4.metric("Status", final_state.get("status", "").value)

            st.markdown(STARFIELD_HTML, unsafe_allow_html=True)