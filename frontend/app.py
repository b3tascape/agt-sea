"""
agt_sea — Streamlit Frontend (Chartreuse Theme)

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
# Chartreuse Theme — Custom CSS
# ---------------------------------------------------------------------------

THEME_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400;1,500;1,600&family=Montserrat:wght@600;700&family=Roboto+Mono:wght@300;400;500&family=Roboto:wght@300;400;500&family=JetBrains+Mono:wght@300;400&display=swap');

    :root {
        --chartreuse: #eeff41;
        --black: #1a1a1a;
        --dark-grey: #2a2a2a;
        --mid-grey: #555555;
        --light-grey: #888888;
        --white: #fafafa;
        --border: #1a1a1a;
        --heading-font: 'Cormorant Garamond', Georgia, serif;
        --alt-heading-font: 'proxima-nova', 'Montserrat', Helvetica, sans-serif;
        --body-font: 'Roboto Mono', 'Roboto', Helvetica, sans-serif;
        --mono-font: 'JetBrains Mono', monospace;
    }

    /* --- Global background --- */
    .stApp {
        background-color: var(--chartreuse) !important;
    }

    /* --- Sidebar --- */
    section[data-testid="stSidebar"] {
        background-color: var(--chartreuse) !important;
        border-right: 1.5px solid var(--black) !important;
    }

    section[data-testid="stSidebar"] .stMarkdown p {
        font-family: var(--body-font) !important;
        font-size: 14px !important;
        font-weight: 300 !important;
        color: var(--black) !important;
        line-height: 1.65 !important;
    }

    section[data-testid="stSidebar"] .stMarkdown strong {
        font-family: var(--body-font) !important;
        font-weight: 500 !important;
    }

    section[data-testid="stSidebar"] h1 {
        font-family: var(--heading-font) !important;
        font-style: normal !important;
        font-weight: 400 !important;
        font-size: 28px !important;
        color: var(--black) !important;
        letter-spacing: -0.5px;
    }

    section[data-testid="stSidebar"] .stSelectbox label {
        font-family: var(--alt-heading-font) !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        color: var(--black) !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }

    /* --- Horizontal rules --- */
    hr {
        border: none !important;
        border-top: 1px solid var(--black) !important;
        opacity: 0.3 !important;
    }

    section[data-testid="stSidebar"] hr {
        border: none !important;
        border-top: 1px solid var(--black) !important;
        opacity: 0.3 !important;
    }

    /* --- Main title --- */
    .stApp h1 {
        font-family: var(--heading-font) !important;
        font-style: normal !important;
        font-weight: 400 !important;
        font-size: 48px !important;
        color: var(--black) !important;
        letter-spacing: -1px;
    }

    /* --- Subheaders (h3) — Cormorant Garamond italic, lowercase --- */
    .stApp h3 {
        font-family: var(--heading-font) !important;
        font-style: italic !important;
        font-weight: 400 !important;
        font-size: 22px !important;
        color: var(--black) !important;
        letter-spacing: -0.3px;
    }

    /* --- Body text --- */
    .stApp .stMarkdown p,
    .stApp .stMarkdown li {
        font-family: var(--body-font) !important;
        font-size: 14px !important;
        font-weight: 300 !important;
        color: var(--black) !important;
        line-height: 1.7 !important;
    }

    .stApp .stMarkdown strong {
        font-weight: 500 !important;
    }

    /* --- Code / mono --- */
    .stApp .stMarkdown code {
        font-family: var(--mono-font) !important;
        font-size: 13px !important;
        font-weight: 300 !important;
        color: var(--black) !important;
        background-color: rgba(0, 0, 0, 0.06) !important;
        padding: 2px 6px !important;
        border-radius: 0px !important;
    }

    /* --- Text area --- */
    .stTextArea textarea {
        font-family: var(--body-font) !important;
        font-size: 14px !important;
        font-weight: 300 !important;
        color: var(--black) !important;
        background-color: rgba(255, 255, 255, 0.35) !important;
        border: 1.5px solid var(--black) !important;
        border-radius: 0px !important;
    }

    .stTextArea textarea:focus {
        border-color: var(--black) !important;
        box-shadow: none !important;
    }

    .stTextArea textarea::placeholder {
        color: var(--mid-grey) !important;
        font-family: var(--body-font) !important;
        font-weight: 300 !important;
        font-style: italic !important;
    }

    .stTextArea label {
        font-family: var(--alt-heading-font) !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        color: var(--black) !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }

    /* --- Primary button --- */
    .stButton > button[kind="primary"],
    .stButton > button {
        font-family: var(--alt-heading-font) !important;
        font-size: 12px !important;
        font-weight: 700 !important;
        color: var(--chartreuse) !important;
        background-color: var(--black) !important;
        border: 1.5px solid var(--black) !important;
        border-radius: 0px !important;
        padding: 10px 28px !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        transition: all 0.15s ease !important;
    }

    .stButton > button:hover {
        background-color: var(--dark-grey) !important;
        color: var(--chartreuse) !important;
    }

    .stButton > button:active {
        background-color: var(--black) !important;
    }

    /* --- Select box --- */
    .stSelectbox > div > div {
        font-family: var(--body-font) !important;
        font-size: 14px !important;
        font-weight: 300 !important;
        background-color: rgba(255, 255, 255, 0.35) !important;
        color: var(--black) !important;
        border: 1.5px solid var(--black) !important;
        border-radius: 0px !important;
    }

    /* --- Expander --- */
    details {
        border: 1.5px solid var(--black) !important;
        border-radius: 0px !important;
        background-color: rgba(255, 255, 255, 0.15) !important;
    }

    details summary {
        font-family: var(--heading-font) !important;
        font-style: italic !important;
        font-weight: 400 !important;
        font-size: 16px !important;
        color: var(--black) !important;
    }

    details[open] {
        background-color: rgba(255, 255, 255, 0.25) !important;
    }

    .streamlit-expanderContent {
        background-color: transparent !important;
    }

    /* --- Status containers --- */
    [data-testid="stStatusWidget"] {
        background-color: rgba(255, 255, 255, 0.15) !important;
        border: 1.5px solid var(--black) !important;
        border-radius: 0px !important;
    }

    /* --- Metrics --- */
    [data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.2) !important;
        border: 1.5px solid var(--black) !important;
        border-radius: 0px !important;
        padding: 14px !important;
    }

    [data-testid="stMetricLabel"] {
        font-family: var(--alt-heading-font) !important;
        font-size: 10px !important;
        font-weight: 700 !important;
        color: var(--black) !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }

    [data-testid="stMetricValue"] {
        font-family: var(--heading-font) !important;
        font-style: italic !important;
        font-size: 22px !important;
        font-weight: 400 !important;
        color: var(--black) !important;
    }

    /* --- Success / Warning banners --- */
    [data-testid="stAlert"] {
        border-radius: 0px !important;
        font-family: var(--body-font) !important;
        font-size: 14px !important;
        font-weight: 300 !important;
        border: 1.5px solid var(--black) !important;
    }

    .stSuccess {
        background-color: rgba(255, 255, 255, 0.3) !important;
    }

    .stWarning {
        background-color: rgba(255, 255, 255, 0.3) !important;
    }

    /* --- Columns text --- */
    .stColumn .stMarkdown strong {
        font-family: var(--alt-heading-font) !important;
        font-size: 10px !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* --- Tooltip --- */
    .stTooltipIcon {
        color: var(--mid-grey) !important;
    }

    /* --- Force black text inside status and expander containers --- */
    [data-testid="stStatusWidget"] h1,
    [data-testid="stStatusWidget"] h2,
    [data-testid="stStatusWidget"] h3,
    [data-testid="stStatusWidget"] h4,
    [data-testid="stStatusWidget"] h5,
    [data-testid="stStatusWidget"] h6,
    [data-testid="stStatusWidget"] p,
    [data-testid="stStatusWidget"] strong,
    [data-testid="stStatusWidget"] b,
    [data-testid="stStatusWidget"] span,
    [data-testid="stStatusWidget"] li,
    [data-testid="stStatusWidget"] .stMarkdown,
    [data-testid="stStatusWidget"] .stMarkdown p,
    [data-testid="stStatusWidget"] .stMarkdown strong {
        color: var(--black) !important;
    }

    details h1, details h2, details h3,
    details h4, details h5, details h6,
    details p, details strong, details b,
    details span, details li,
    details .stMarkdown,
    details .stMarkdown p,
    details .stMarkdown strong {
        color: var(--black) !important;
    }

    .streamlit-expanderContent h1,
    .streamlit-expanderContent h2,
    .streamlit-expanderContent h3,
    .streamlit-expanderContent h4,
    .streamlit-expanderContent h5,
    .streamlit-expanderContent h6,
    .streamlit-expanderContent p,
    .streamlit-expanderContent strong,
    .streamlit-expanderContent b,
    .streamlit-expanderContent span,
    .streamlit-expanderContent li,
    .streamlit-expanderContent .stMarkdown,
    .streamlit-expanderContent .stMarkdown p,
    .streamlit-expanderContent .stMarkdown strong {
        color: var(--black) !important;
    }

    /* --- Footer badge --- */
    .footer-badge {
        font-family: var(--body-font);
        font-size: 11px;
        font-weight: 300;
        color: var(--mid-grey);
        text-align: right;
        padding-top: 40px;
        letter-spacing: 0.5px;
    }
</style>
"""

st.markdown(THEME_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — inputs
# ---------------------------------------------------------------------------

st.sidebar.markdown("# { agt_sea }")
st.sidebar.markdown("---")

# Creative philosophy selector
philosophy_labels = {
    CreativePhilosophy.BOLD_AND_DISRUPTIVE: "bold & disruptive",
    CreativePhilosophy.MINIMAL_AND_REFINED: "minimal & refined",
    CreativePhilosophy.EMOTIONALLY_DRIVEN: "emotionally driven",
    CreativePhilosophy.DATA_LED: "data led",
    CreativePhilosophy.CULTURALLY_PROVOCATIVE: "culturally provocative",
}

selected_philosophy = st.sidebar.selectbox(
    "CREATIVE PHILOSOPHY",
    options=list(philosophy_labels.keys()),
    format_func=lambda x: philosophy_labels[x],
    help="Sets the Creative Director's evaluation lens.",
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "Submit a client brief and watch three AI agents "
    "collaborate — a `strategist` writes the creative brief, a `creative` "
    "generates ideas, and a `creative director` evaluates the work."
)
st.sidebar.markdown("---")
st.sidebar.markdown(
    '<div class="footer-badge">SM λ ©</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Main area — brief input
# ---------------------------------------------------------------------------

st.title("{ agt_sea }")
st.markdown("### submit your brief")

brief_text = st.text_area(
    "CLIENT BRIEF",
    height=200,
    placeholder=(
        "Describe your brand, target audience, campaign objectives, "
        "channels, budget, and timeline..."
    ),
)

run_button = st.button(
    "RUN PIPELINE",
    type="primary",
    disabled=not brief_text,
)

# ---------------------------------------------------------------------------
# Pipeline execution with live progress
# ---------------------------------------------------------------------------

if run_button and brief_text:
    graph = build_graph()

    initial_state = AgencyState(
        client_brief=brief_text,
        creative_philosophy=selected_philosophy,
    )

    progress_container = st.container()
    results_container = st.container()

    with progress_container:
        st.markdown("---")
        st.markdown("### pipeline executing...")

        final_state = None
        node_labels = {
            "strategist": ("strategist", "writing creative brief..."),
            "creative": ("creative", "generating ideas..."),
            "creative_director": ("creative director", "evaluating work..."),
            "check_iterations": ("iteration check", "checking iteration limit..."),
            "finalise_approved": ("approved", "creative work approved."),
            "finalise_max_iterations": ("max iterations", "selecting best work..."),
        }

        for event in graph.stream(initial_state):
            for node_name, node_output in event.items():
                label, description = node_labels.get(
                    node_name, (node_name, "processing...")
                )

                with st.status(f"{label}", expanded=False) as status:
                    st.write(description)

                    if node_name == "strategist":
                        st.markdown("**creative brief (preview):**")
                        st.markdown(node_output.get("creative_brief", "")[:500] + "...")
                        status.update(label=f"{label} ✓", state="complete")

                    elif node_name == "creative":
                        iteration = node_output.get("iteration", 0)
                        st.markdown(f"**iteration {iteration} — concepts (preview):**")
                        st.markdown(node_output.get("creative_concept", "")[:500] + "...")
                        status.update(
                            label=f"{label} · iteration {iteration} ✓",
                            state="complete",
                        )

                    elif node_name == "creative_director":
                        evaluation = node_output.get("cd_evaluation")
                        if evaluation:
                            st.metric("score", f"{evaluation.score}/100")
                            st.markdown(f"**direction:** {evaluation.direction}")
                        status.update(label=f"{label} ✓", state="complete")

                    elif node_name in ("finalise_approved", "finalise_max_iterations"):
                        status.update(label=f"{label}", state="complete")

                    else:
                        status.update(label=f"{label} ✓", state="complete")

                final_state = node_output

    # ---------------------------------------------------------------------------
    # Results
    # ---------------------------------------------------------------------------

    if final_state:
        with results_container:
            st.markdown("---")

            status = final_state.get("status")
            if status == WorkflowStatus.APPROVED:
                st.success("creative work approved.")
            elif status == WorkflowStatus.MAX_ITERATIONS_REACHED:
                st.warning("max iterations reached — showing best scoring idea.")

            st.markdown("### final creative concept")
            st.markdown(final_state.get("creative_concept", ""))

            st.markdown("---")
            st.markdown("### pipeline history")

            history = final_state.get("history", [])
            iteration = 0

            for entry in history:
                if entry.agent == AgentRole.STRATEGIST:
                    with st.expander("strategist — creative brief"):
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
                        f"creative — iteration {iteration}"
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
                        f"creative director — iteration {iteration} "
                        f"· score: {entry.evaluation.score}/100"
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
                            st.metric("score", f"{entry.evaluation.score}/100")
                        with detail_col:
                            st.markdown("**Strengths:**")
                            for s in entry.evaluation.strengths:
                                st.markdown(f"- {s}")
                            st.markdown("**Weaknesses:**")
                            for w in entry.evaluation.weaknesses:
                                st.markdown(f"- {w}")

                        st.markdown(f"**Direction:** {entry.evaluation.direction}")

            st.markdown("---")
            st.markdown("### run metadata")
            meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
            meta_col1.metric("iterations", final_state.get("iteration", 0))
            meta_col2.metric("history", len(history))
            meta_col3.metric(
                "philosophy",
                philosophy_labels.get(selected_philosophy, ""),
            )
            meta_col4.metric("status", final_state.get("status", "").value)

            st.markdown(
                '<div class="footer-badge">SM λ ©</div>',
                unsafe_allow_html=True,
            )