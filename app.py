from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import streamlit as st
from agent import careeros_graph, create_initial_state

# Navigation and Result Configuration
NAV_ITEMS = [
    "Dynamic Dashboard",
    "CV Versions Hub",
    "Job Intelligence",
    "Outreach",
    "Interview Prep",
    "Control Tower",
]
RESULT_KEYS = (
    "profile_data",
    "job_listings",
    "tailored_cv",
    "tailored_cv_path",
    "outreach_draft",
    "interview_prep",
    "agent_metrics",
    "api_metrics",
    "ats_score",
)

st.set_page_config(
    page_title="CareerOS | Digital FTE",
    page_icon=":material/bolt:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Session State
for key, value in {
    "profile_data": {},
    "job_listings": [],
    "tailored_cv": "",
    "tailored_cv_path": "",
    "outreach_draft": "",
    "interview_prep": [],
    "z_axis_approved": False,
    "agent_metrics": {},
    "api_metrics": {},
    "ats_score": 0,
    "pipeline_ready": False,
    "pipeline_error": "",
    "pipeline_events": [],
    "live_agent_text": {},
    "thread_id": "",
    "rpa_result": {},
    "target_role": "AI Engineer",
    "groq_api_key": "",
    "gemini_api_key": "",
    "pinecone_api_key": "",
    "pinecone_index_name": "",
    "adzuna_app_id": "",
    "adzuna_app_key": "",
    "jsearch_api_key": "",
    "ats_strictness": 60,
    "ui_theme": "dark",
}.items():
    st.session_state.setdefault(key, value)

theme_tokens = {
    "dark": {
        "bg": "#0B0F19",
        "panel": "rgba(26, 31, 43, 0.94)",
        "panel_soft": "rgba(26, 31, 43, 0.72)",
        "sidebar": "#101725",
        "accent": "#00E5FF",
        "accent_alt": "#B300FF",
        "text": "#F3F6FC",
        "muted": "#99A6BA",
        "border": "rgba(149, 170, 199, 0.20)",
        "input": "#151B28",
        "button_text": "#07111B",
    },
    "light": {
        "bg": "#F7F1E8",
        "panel": "rgba(255, 252, 247, 0.96)",
        "panel_soft": "rgba(238, 229, 217, 0.78)",
        "sidebar": "#EEE5D9",
        "accent": "#8B1E3F",
        "accent_alt": "#B34A69",
        "text": "#33252A",
        "muted": "#74646A",
        "border": "rgba(93, 59, 70, 0.20)",
        "input": "#FFFDF9",
        "button_text": "#FFFFFF",
    },
}[st.session_state["ui_theme"]]

st.markdown(
    f"""
    <style>
    :root {{
        --cos-bg: {theme_tokens['bg']};
        --cos-panel: {theme_tokens['panel']};
        --cos-panel-soft: {theme_tokens['panel_soft']};
        --cos-sidebar: {theme_tokens['sidebar']};
        --cos-accent: {theme_tokens['accent']};
        --cos-accent-alt: {theme_tokens['accent_alt']};
        --cos-text: {theme_tokens['text']};
        --cos-muted: {theme_tokens['muted']};
        --cos-border: {theme_tokens['border']};
        --cos-input: {theme_tokens['input']};
        --cos-button-text: {theme_tokens['button_text']};
    }}
    [data-testid="stAppViewContainer"] {{
        background: var(--cos-bg) !important;
        color: var(--cos-text) !important;
    }}
    [data-testid="stHeader"] {{
        background: transparent !important;
        visibility: visible !important;
        height: 2.75rem !important;
    }}
    [data-testid="stSidebar"] {{
        background: var(--cos-sidebar) !important;
        border-right: 1px solid var(--cos-border);
    }}
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
        gap: 0.55rem;
    }}
    [data-testid="stAppViewBlockContainer"] {{ max-width: 1480px; padding-top: 1.3rem; }}
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background: var(--cos-panel-soft);
        border: 1px solid var(--cos-border) !important;
        border-radius: 12px !important;
    }}
    [data-testid="stMetric"] {{
        background: var(--cos-panel);
        border: 1px solid var(--cos-border);
        border-radius: 12px;
        padding: 14px 16px;
    }}
    [data-testid="stMetricLabel"] p, .stCaption {{
        color: var(--cos-muted) !important;
    }}
    h1, h2, h3 {{ color: var(--cos-text) !important; }}
    a, [data-testid="stMarkdownContainer"] a {{ color: var(--cos-accent) !important; }}
    [data-testid="stBaseButton-primary"] {{
        background: linear-gradient(105deg, var(--cos-accent), var(--cos-accent-alt)) !important;
        color: var(--cos-button-text) !important;
        border: 0 !important;
        border-radius: 9px !important;
        font-weight: 700 !important;
        box-shadow: 0 0 18px color-mix(in srgb, var(--cos-accent) 22%, transparent);
    }}
    [data-testid="stBaseButton-secondary"] {{
        border: 1px solid var(--cos-border) !important;
        border-radius: 9px !important;
    }}
    [data-testid="stRadio"] label[data-checked="true"] p {{
        color: var(--cos-accent) !important;
        font-weight: 700;
    }}
    [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
    [data-testid="stFileUploader"] section, [data-testid="stSelectbox"] div {{
        background-color: var(--cos-input) !important;
        border-color: var(--cos-border) !important;
        border-radius: 8px !important;
    }}
    [data-testid="stDataFrame"] {{
        border: 1px solid var(--cos-border);
        border-radius: 12px;
        overflow: hidden;
    }}
    [data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"] {{
        position: fixed !important;
        top: 0.45rem !important;
        right: 3.5rem !important;
        z-index: 10001 !important;
        visibility: visible !important;
        opacity: 1 !important;
        background: var(--cos-panel) !important;
        border: 1px solid var(--cos-border) !important;
        border-radius: 8px !important;
    }}
    #MainMenu, footer {{ visibility: hidden; height: 0; }}
    </style>
    """,
    unsafe_allow_html=True,
)

def _token_total() -> int:
    return sum(
        int(metric.get("total_tokens", 0) or 0)
        for metric in st.session_state["agent_metrics"].values()
        if isinstance(metric, dict)
    )

def _render_metrics() -> None:
    metrics = st.session_state["api_metrics"]
    adzuna = (metrics.get("adzuna") or {}).get("remaining")
    jsearch = (metrics.get("jsearch") or {}).get("remaining")
    quota = "Waiting" if not metrics else (
        f"A: {adzuna if adzuna is not None else '--'} · "
        f"J: {jsearch if jsearch is not None else '--'}"
    )
    columns = st.columns(3)
    columns[0].metric("Job API quota", quota)
    score = st.session_state["ats_score"]
    columns[1].metric("ATS skill alignment", f"{score}%" if score else "--")
    columns[2].metric("Agent tokens", f"{_token_total():,}")

def _clear_run() -> None:
    for key in RESULT_KEYS:
        if key in {"profile_data", "agent_metrics", "api_metrics"}:
            st.session_state[key] = {}
        elif key in {"job_listings", "interview_prep"}:
            st.session_state[key] = []
        elif key == "ats_score":
            st.session_state[key] = 0
        else:
            st.session_state[key] = ""
    st.session_state.update(
        pipeline_ready=False,
        pipeline_error="",
        pipeline_events=[],
        live_agent_text={},
        thread_id="",
        rpa_result={},
        z_axis_approved=False,
    )

def _run_pipeline_direct(role: str, pdf_bytes: bytes, event_slot: Any, token_slot: Any) -> None:
    _clear_run()

    run_id = f"run-{uuid4().hex[:12]}"
    config = {
        "configurable": {
            "credentials": {
                "GOOGLE_API_KEY": st.session_state["gemini_api_key"],
                "GROQ_API_KEY": st.session_state["groq_api_key"],
                "PINECONE_API_KEY": st.session_state["pinecone_api_key"],
                "PINECONE_INDEX_NAME": st.session_state["pinecone_index_name"],
                "ADZUNA_APP_ID": st.session_state["adzuna_app_id"],
                "ADZUNA_APP_KEY": st.session_state["adzuna_app_key"],
                "JSEARCH_API_KEY": st.session_state["jsearch_api_key"],
            },
            "thread_id": run_id
        }
    }

    state = create_initial_state()
    state.update({
        "target_role": role.strip(),
        "resume_pdf_bytes": pdf_bytes,
        "resume_filename": "resume.pdf",
        "run_id": run_id,
        "ats_strictness": st.session_state["ats_strictness"],
    })

    try:
        # execute graph directly in memory
        final_state = careeros_graph.invoke(state, config=config)

        # Update session state with results
        for key in RESULT_KEYS:
            if key in final_state:
                st.session_state[key] = final_state[key]

        st.session_state["pipeline_ready"] = True
        st.session_state["pipeline_events"].append({"node": "pipeline", "status": "Completed successfully in-memory"})

    except Exception as error:
        st.session_state["pipeline_error"] = f"In-memory pipeline failed: {str(error)}"

def _authorize_direct() -> None:
    st.session_state["z_axis_approved"] = True
    st.session_state["rpa_result"] = {"message": "Simulated Success for Cloud Demo"}

with st.sidebar:
    st.markdown("## CAREEROS")
    st.caption("AUTONOMOUS CAREER SYSTEM")
    navigation = st.radio("Navigation", NAV_ITEMS, key="navigation")
    st.divider()
    st.markdown("**Z-AXIS GOVERNANCE**")
    if st.session_state["z_axis_approved"]:
        st.success("Approval recorded")
    elif st.session_state["pipeline_ready"]:
        st.warning("Review staged · execution blocked")
    else:
        st.caption("No active authorization")

    if st.button(
        "Authorize Playwright RPA",
        type="primary",
        icon=":material/lock_open:",
        disabled=not st.session_state["pipeline_ready"] or st.session_state["z_axis_approved"],
        key="authorize_rpa",
    ):
        _authorize_direct()

    if st.session_state["rpa_result"]:
        st.info(st.session_state["rpa_result"].get("message", "Browser preparation complete."))

    st.slider("ATS strictness", min_value=0, max_value=100, key="ats_strictness")
    with st.expander("⚙️ System Credentials", expanded=False):
        st.caption("Credentials are required for in-memory execution.")
        st.text_input("Groq API key", type="password", key="groq_api_key")
        st.text_input("Gemini API key", type="password", key="gemini_api_key")
        st.text_input("Pinecone API key", type="password", key="pinecone_api_key")
        st.text_input("Pinecone index name", key="pinecone_index_name")
        st.text_input("Adzuna app ID", type="password", key="adzuna_app_id")
        st.text_input("Adzuna app key", type="password", key="adzuna_app_key")
        st.text_input("JSearch API key", type="password", key="jsearch_api_key")

def _page_header(eyebrow: str, title: str, description: str) -> None:
    st.caption(eyebrow.upper())
    st.title(title)
    st.caption(description)

top_brand, top_theme = st.columns([8, 1], vertical_alignment="center")
with top_brand:
    st.markdown("**CAREEROS**　<span style='color:var(--cos-muted)'>AUTONOMOUS CAREER WORKSPACE</span>", unsafe_allow_html=True)
with top_theme:
    is_dark = st.session_state["ui_theme"] == "dark"
    if st.button(
        "Light theme" if is_dark else "Dark theme",
        icon=":material/light_mode:" if is_dark else ":material/dark_mode:",
        help="Switch the app's color theme",
        key="toggle_theme",
    ):
        st.session_state["ui_theme"] = "light" if is_dark else "dark"
        st.rerun()

if navigation == "Dynamic Dashboard":
    _page_header("Workspace / Overview", "CareerOS", "Your live career pipeline, from verified profile to human-reviewed application.")
    with st.container(border=True):
        st.caption("START A NEW RUN")
        role_column, resume_column = st.columns([1, 1.4], vertical_alignment="bottom")
        with role_column:
            role = st.text_input("Target role", key="target_role")
        with resume_column:
            uploaded_pdf = st.file_uploader("Upload resume PDF", type=["pdf"], key="resume_pdf")
        start = st.button(
            "Run career pipeline",
            type="primary",
            icon=":material/bolt:",
            disabled=uploaded_pdf is None,
        )
    _render_metrics()
    event_output = st.container(border=True)
    token_output = st.container(border=True)
    if start and uploaded_pdf is not None:
        with st.spinner("Executing Agentic Pipeline in-memory..."):
            _run_pipeline_direct(role, uploaded_pdf.getvalue(), event_output, token_output)
        if st.session_state["pipeline_error"]:
            st.error(st.session_state["pipeline_error"])
        elif st.session_state["pipeline_ready"]:
            st.success("Materials are staged for review. Cloud demo uses simulated RPA.")
    elif st.session_state["pipeline_error"]:
        st.error(st.session_state["pipeline_error"])

    if st.session_state.get("pipeline_events", []):
        with event_output:
            for item in st.session_state["pipeline_events"][-18:]:
                st.caption(f"{str(item['node']).replace('_', ' ').title()} · {item['status']}")

    if st.session_state["profile_data"]:
        profile = st.session_state["profile_data"]
        with st.container(border=True):
            st.subheader(profile.get("name", "Verified candidate"))
            st.write(profile.get("summary", ""))
            if profile.get("skills"):
                st.caption("Verified skills · " + " / ".join(profile["skills"]))

elif navigation == "CV Versions Hub":
    _page_header("Workspace / Documents", "CV Versions Hub", "Review and export the role-specific version built from verified profile facts.")
    if st.session_state["tailored_cv"]:
        st.markdown(st.session_state["tailored_cv"])
    else:
        st.info("Run the pipeline to create a tailored CV.")

elif navigation == "Job Intelligence":
    _page_header("Workspace / Market", "Job Intelligence", "Live roles gathered from Adzuna and JSearch, normalized and deduplicated.")
    _render_metrics()
    jobs = st.session_state["job_listings"]
    if jobs:
        st.dataframe(jobs, hide_index=True)
    else:
        st.info("No live listings yet. Run the pipeline from Dynamic Dashboard.")

elif navigation == "Outreach":
    _page_header("Workspace / Communication", "Outreach", "A contextual hiring-manager outline grounded in the profile and selected job.")
    if st.session_state["outreach_draft"]:
        st.markdown(st.session_state["outreach_draft"])
    else:
        st.info("Your outreach draft appears after the pipeline runs.")

elif navigation == "Interview Prep":
    _page_header("Workspace / Practice", "Interview Prep", "Role-specific behavioral questions designed for STAR responses.")
    if st.session_state["interview_prep"]:
        for index, question in enumerate(st.session_state["interview_prep"], start=1):
            with st.container(border=True):
                st.caption(f"STAR PROMPT {index:02d}")
                st.write(question)
    else:
        st.info("Interview prompts appear after the pipeline runs.")

elif navigation == "Control Tower":
    _page_header("Governance / Human in the loop", "Control Tower", "Execution remains blocked until you explicitly authorize the staged browser workflow.")
    if st.session_state["z_axis_approved"]:
        st.success("Z-AXIS UNLOCKED · Approval recorded for this run.")
    elif st.session_state["pipeline_ready"]:
        st.warning("Materials are staged. Review the profile, job, CV, outreach, and interview prompts before approval.")
    else:
        st.info("No staged run. Start from Dynamic Dashboard.")
    _render_metrics()
    if st.session_state["rpa_result"]:
        st.write(st.session_state["rpa_result"].get("message", "Browser preparation complete."))
    if st.session_state.get("pipeline_events", []):
        st.subheader("Run trace")
        for item in st.session_state["pipeline_events"][-30:]:
            st.markdown(f"`{str(item['node']).replace('_', ' ').title()}` · {item['status']}")
