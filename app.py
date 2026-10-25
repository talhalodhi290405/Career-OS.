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
    "assistant_messages": [],
}.items():
    st.session_state.setdefault(key, value)

theme_tokens = {
    "dark": {
        "bg": "#050811",
        "panel": "rgba(12, 19, 32, 0.97)",
        "panel_soft": "rgba(9, 16, 29, 0.88)",
        "sidebar": "#070D19",
        "accent": "#00D9FF",
        "accent_alt": "#1677FF",
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
    [data-testid="stSidebar"] > div:first-child {{
        background:
            radial-gradient(ellipse at 12% 0%, color-mix(in srgb, var(--cos-accent) 11%, transparent), transparent 48%),
            var(--cos-sidebar);
    }}
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 {{
        letter-spacing: .12em;
        font-size: 1.02rem;
        margin-bottom: .15rem;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] > label {{
        color: var(--cos-muted);
        font-size: .72rem;
        font-weight: 750;
        letter-spacing: .13em;
        text-transform: uppercase;
        margin-bottom: .45rem;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {{
        gap: .32rem;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label {{
        position: relative;
        padding: .58rem .65rem;
        margin: 0;
        border: 1px solid transparent;
        border-radius: 10px;
        background: transparent;
        transition: background .18s ease, border-color .18s ease, transform .18s ease;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label:hover {{
        background: var(--cos-panel-soft);
        border-color: var(--cos-border);
        transform: translateX(2px);
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {{
        background: linear-gradient(100deg, color-mix(in srgb, var(--cos-accent) 14%, transparent), color-mix(in srgb, var(--cos-accent-alt) 9%, transparent));
        border-color: color-mix(in srgb, var(--cos-accent) 36%, var(--cos-border));
        box-shadow: inset 3px 0 0 var(--cos-accent), 0 5px 18px rgba(0,0,0,.08);
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label p {{
        font-size: .86rem;
        font-weight: 560;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) p {{
        color: var(--cos-text) !important;
        font-weight: 750;
    }}
    .cos-side-brand {{
        padding: .9rem .85rem;
        margin: .15rem 0 .35rem;
        border: 1px solid var(--cos-border);
        border-radius: 14px;
        background: linear-gradient(145deg, var(--cos-panel), color-mix(in srgb, var(--cos-accent) 5%, var(--cos-sidebar)));
        box-shadow: 0 10px 28px rgba(0,0,0,.10);
    }}
    .cos-brand-row {{ display:flex; align-items:center; gap:.65rem; }}
    .cos-brand-mark {{
        display:flex; align-items:center; justify-content:center;
        width:2.45rem; height:2.45rem; flex-shrink:0;
        border-radius:11px; color:var(--cos-button-text);
        background:linear-gradient(135deg,var(--cos-accent),var(--cos-accent-alt));
        font-size:1.25rem; font-weight:900;
        box-shadow:0 0 22px color-mix(in srgb,var(--cos-accent) 25%,transparent);
    }}
    .cos-brand-name {{ color:var(--cos-text); font-weight:850; letter-spacing:.12em; font-size:.93rem; }}
    .cos-brand-sub {{ color:var(--cos-muted); font-size:.62rem; letter-spacing:.1em; margin-top:.18rem; }}
    .cos-side-status {{
        display:flex; align-items:center; gap:.45rem;
        margin-top:.8rem; padding-top:.7rem; border-top:1px solid var(--cos-border);
        color:var(--cos-muted); font-size:.72rem;
    }}
    .cos-live-dot {{ width:.45rem; height:.45rem; border-radius:50%; background:#22c55e; box-shadow:0 0 10px #22c55e88; }}
    .cos-side-label {{
        color:var(--cos-muted); font-size:.67rem; font-weight:800;
        letter-spacing:.13em; margin:.55rem 0 .15rem;
    }}
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {{
        width:100%;
        min-height:2.6rem;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] {{
        border:1px solid var(--cos-border);
        border-radius:10px;
        background:var(--cos-panel-soft);
    }}
    [data-testid="stAppViewBlockContainer"] {{ max-width: 1480px; padding-top: 1.3rem; }}
    [data-testid="stAppViewContainer"] {{
        background-image: radial-gradient(ellipse at 78% 0%, color-mix(in srgb, var(--cos-accent) 7%, transparent), transparent 34%);
    }}
    [data-testid="stMetric"] {{
        box-shadow: 0 0 0 1px color-mix(in srgb, var(--cos-accent) 5%, transparent), 0 10px 28px rgba(0,0,0,.10);
        transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
    }}
    [data-testid="stMetric"]:hover {{
        transform: translateY(-2px);
        border-color: color-mix(in srgb, var(--cos-accent) 55%, var(--cos-border));
        box-shadow: 0 0 22px color-mix(in srgb, var(--cos-accent) 10%, transparent);
    }}
    [data-testid="stVerticalBlockBorderWrapper"] {{
        box-shadow: 0 8px 28px rgba(0,0,0,.07);
        transition: border-color .18s ease, box-shadow .18s ease;
    }}
    [data-testid="stBaseButton-primary"]:hover {{
        filter: brightness(1.08);
        box-shadow: 0 0 25px color-mix(in srgb, var(--cos-accent) 30%, transparent);
        transform: translateY(-1px);
    }}
    .cos-hero {{
        padding: 1.1rem 1.25rem; border-radius: 16px; margin: .35rem 0 1rem;
        border: 1px solid var(--cos-border);
        background: linear-gradient(115deg, color-mix(in srgb, var(--cos-accent) 10%, var(--cos-panel)), var(--cos-panel) 62%, color-mix(in srgb, var(--cos-accent-alt) 8%, var(--cos-panel)));
        box-shadow: 0 12px 38px rgba(0,0,0,.08);
    }}
    .cos-hero-kicker {{ color:var(--cos-accent); font-size:.68rem; font-weight:850; letter-spacing:.16em; text-transform:uppercase; }}
    .cos-hero-title {{ color:var(--cos-text); font-size:1.55rem; font-weight:850; letter-spacing:-.035em; margin:.28rem 0; }}
    .cos-hero-copy {{ color:var(--cos-muted); font-size:.88rem; }}
    .cos-assistant {{ border:1px solid var(--cos-border); border-radius:16px; padding:1rem; background:linear-gradient(140deg,var(--cos-panel),var(--cos-panel-soft)); box-shadow:0 10px 28px rgba(0,0,0,.08); }}
    .cos-assistant-label {{ color:var(--cos-accent); font-size:.68rem; font-weight:850; letter-spacing:.14em; }}
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
    /* Shared contrast rules for all theme surfaces */
    [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"],
    [data-testid="stAppViewContainer"] p,
    [data-testid="stAppViewContainer"] li,
    [data-testid="stAppViewContainer"] label,
    [data-testid="stAppViewContainer"] span,
    [data-testid="stAppViewContainer"] small,
    [data-testid="stMetricValue"],
    [data-testid="stMetricValue"] div {{
        color: var(--cos-text);
    }}
    [data-testid="stCaptionContainer"], .stCaption,
    [data-testid="stWidgetLabel"] p,
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p {{
        color: var(--cos-muted) !important;
    }}
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input,
    [data-testid="stTimeInput"] input,
    [data-baseweb="select"] input,
    [data-baseweb="select"] [role="combobox"] {{
        color: var(--cos-text) !important;
        -webkit-text-fill-color: var(--cos-text) !important;
        background: var(--cos-input) !important;
        border-color: var(--cos-border) !important;
        caret-color: var(--cos-accent) !important;
    }}
    [data-testid="stExpander"], [data-testid="stExpander"] details,
    [data-testid="stExpander"] summary, [data-testid="stChatMessage"],
    [data-testid="stAlert"], [data-testid="stNotification"] {{
        color: var(--cos-text) !important;
        border-color: var(--cos-border) !important;
        background-color: var(--cos-panel) !important;
    }}
    [data-testid="stTabs"] button,
    [data-testid="stRadio"] label,
    [data-testid="stCheckbox"] label,
    [data-testid="stToggle"] label,
    [data-testid="stSlider"] label {{
        color: var(--cos-text) !important;
    }}
    [data-testid="stTabs"] button[aria-selected="true"] {{
        color: var(--cos-accent) !important;
        border-bottom-color: var(--cos-accent) !important;
    }}
    [data-baseweb="popover"], [data-baseweb="menu"],
    [data-baseweb="select"] [role="listbox"],
    [data-baseweb="select"] [role="option"] {{
        color: var(--cos-text) !important;
        background-color: var(--cos-panel) !important;
        border-color: var(--cos-border) !important;
    }}
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span {{
        color: var(--cos-text);
    }}
    [data-testid="stSidebar"] .cos-side-label,
    [data-testid="stSidebar"] .cos-brand-sub,
    [data-testid="stSidebar"] .cos-side-status {{
        color: var(--cos-muted) !important;
    }}
    [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-secondary"] p {{
        color: var(--cos-text) !important;
        background-color: var(--cos-panel) !important;
        border-color: var(--cos-border) !important;
    }}
    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploader"] section div,
    [data-testid="stFileUploader"] small {{
        color: var(--cos-text) !important;
        border-color: var(--cos-border) !important;
    }}
    [data-testid="stDataFrame"], [data-testid="stTable"] {{
        background: var(--cos-panel) !important;
        color: var(--cos-text) !important;
        border-color: var(--cos-border) !important;
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

def _career_faq_reply(prompt: str) -> str:
    q = prompt.casefold()
    if any(word in q for word in ("how start", "get started", "how do i", "run pipeline", "upload")):
        return "To start: choose a target role, upload a text-readable PDF resume, then select **Run career pipeline**. CareerOS verifies resume facts, searches for matching roles, and stages tailored application materials for your review."
    if any(word in q for word in ("ats", "score", "alignment", "strictness")):
        return "ATS skill alignment compares the verified skills extracted from your resume with the target-role requirements. Use the ATS strictness slider to tune screening sensitivity. A score is only shown after a successful pipeline run."
    if any(word in q for word in ("company", "companies", "jazz", "foodpanda", "bank", "banking", "employer")):
        return "CareerOS is a career workspace, not an employer portal. You can use Job Intelligence to review roles returned by connected job sources. Jazz, Foodpanda, and banks are examples of employers you may research; this demo does not claim a live partnership or show their private internal dashboards."
    if any(word in q for word in ("privacy", "data", "resume", "secure", "security")):
        return "Your uploaded resume is processed by the configured AI services for this run. Review the connected providers and credentials before uploading sensitive information. Avoid sharing API keys in chat or in public screenshots."
    if any(word in q for word in ("human", "approval", "governance", "rpa", "control tower")):
        return "CareerOS keeps a human review gate before the simulated browser/RPA step. Review generated materials first; the demo's authorization action is simulated and does not submit real job applications."
    if any(word in q for word in ("job", "jobs", "search", "listing", "role")):
        count = len(st.session_state.get("job_listings", []))
        return f"CareerOS currently has **{count} job listing(s)** in this session. Run the pipeline with a target role to refresh results, then open Job Intelligence. Available results depend on the configured providers and public fallback availability."
    if any(word in q for word in ("cv", "cover letter", "outreach", "interview")):
        return "After a successful run, open CV Versions Hub for the tailored CV, Outreach for the draft message, and Interview Prep for role-specific practice. Review and edit generated content before using it."
    return "I can help with the CareerOS workflow, resume verification, ATS alignment, job listings, CV/outreach/interview materials, company research, and human-review controls. Try one of the suggested questions below."

def _career_assistant_reply(prompt: str) -> str:
    api_key = st.session_state.get("groq_api_key", "").strip()
    if api_key:
        try:
            from langchain_groq import ChatGroq
            from langchain_core.messages import HumanMessage, SystemMessage
            history = st.session_state.get("assistant_messages", [])[-8:]
            messages = [SystemMessage(content=(
                "You are CareerOS Assist, an informational assistant embedded in a career dashboard. "
                "Answer concisely using only the app context: resume fact verification, job search, ATS skill alignment, tailored CV, outreach, interview prep, and human approval. "
                "Do not claim partnerships with Jazz, Foodpanda, banks, or employers. Do not claim this demo submits real applications; RPA authorization is simulated. "
                "Never ask for or reveal API keys. If asked about live company vacancies, direct the user to Job Intelligence and official employer careers pages."
            ))]
            for item in history:
                role = "assistant" if item.get("role") == "assistant" else "human"
                messages.append(HumanMessage(content=item.get("content", "")) if role == "human" else SystemMessage(content="Previous assistant answer: " + item.get("content", "")))
            messages.append(HumanMessage(content=prompt))
            response = ChatGroq(model="openai/gpt-oss-120b", api_key=api_key, temperature=0.2).invoke(messages)
            answer = str(response.content).strip()
            if answer:
                return answer
        except Exception:
            pass
    return _career_faq_reply(prompt)

def _ask_career_assistant(prompt: str) -> None:
    question = prompt.strip()
    if not question:
        return
    st.session_state["assistant_messages"].append({"role": "user", "content": question})
    answer = _career_assistant_reply(question)
    st.session_state["assistant_messages"].append({"role": "assistant", "content": answer})

def _authorize_direct() -> None:
    st.session_state["z_axis_approved"] = True
    st.session_state["rpa_result"] = {"message": "Simulated Success for Cloud Demo"}

with st.sidebar:
    pipeline_status = (
        "READY FOR REVIEW" if st.session_state["pipeline_ready"]
        else "ATTENTION REQUIRED" if st.session_state["pipeline_error"]
        else "SYSTEM ONLINE"
    )
    st.markdown(
        f"""
        <div class="cos-side-brand">
          <div class="cos-brand-row">
            <div class="cos-brand-mark">C</div>
            <div>
              <div class="cos-brand-name">CAREEROS</div>
              <div class="cos-brand-sub">AUTONOMOUS CAREER SYSTEM</div>
            </div>
          </div>
          <div class="cos-side-status"><span class="cos-live-dot"></span><span>{pipeline_status}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="cos-side-label">WORKSPACE MODULES</div>', unsafe_allow_html=True)
    nav_icons = {
        "Dynamic Dashboard": "◈",
        "CV Versions Hub": "▤",
        "Job Intelligence": "⌕",
        "Outreach": "↗",
        "Interview Prep": "◎",
        "Control Tower": "⛨",
    }
    navigation = st.radio(
        "Navigation",
        NAV_ITEMS,
        format_func=lambda item: f"{nav_icons.get(item, '•')}   {item}",
        key="navigation",
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown('<div class="cos-side-label">Z-AXIS · GOVERNANCE</div>', unsafe_allow_html=True)
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
    st.markdown("""
    <div class="cos-hero">
      <div class="cos-hero-kicker">◈ Career intelligence · Human in control</div>
      <div class="cos-hero-title">Your next opportunity starts here.</div>
      <div class="cos-hero-copy">One workspace for verified profile insights, job discovery, tailored materials, and review-ready actions.</div>
    </div>
    """, unsafe_allow_html=True)
    _page_header("Workspace / Overview", "CareerOS Dashboard", "Your live career pipeline, from verified profile to human-reviewed application.")
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

    st.markdown('<div class="cos-assistant"><div class="cos-assistant-label">✦ CAREEROS ASSIST</div><h3 style="margin:.25rem 0">How can I help?</h3><p style="color:var(--cos-muted);margin:0">Ask about your workflow, job search, ATS score, or application materials.</p></div>', unsafe_allow_html=True)
    quick_col1, quick_col2, quick_col3 = st.columns(3)
    if quick_col1.button("How do I get started?", key="assist_start", use_container_width=True):
        _ask_career_assistant("How do I get started?")
    if quick_col2.button("Explain my ATS score", key="assist_ats", use_container_width=True):
        _ask_career_assistant("Explain my ATS score")
    if quick_col3.button("Company and job info", key="assist_companies", use_container_width=True):
        _ask_career_assistant("How can I find company and job information about Jazz, Foodpanda, and banks?")
    with st.container(border=True):
        for message in st.session_state["assistant_messages"][-10:]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        user_question = st.chat_input("Ask CareerOS Assist…", key="career_assistant_input")
        if user_question:
            _ask_career_assistant(user_question)
            st.rerun()

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
