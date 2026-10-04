from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


API_BASE_URL = os.getenv("CAREEROS_API_URL", "").rstrip("/") or "http://localhost:8000"
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
    "pipeline_events": [],
    "pipeline_error": "",
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


def _api_headers() -> dict[str, str]:
    values = {
        "X-Groq-Api-Key": st.session_state["groq_api_key"],
        "X-Google-Api-Key": st.session_state["gemini_api_key"],
        "X-Pinecone-Api-Key": st.session_state["pinecone_api_key"],
        "X-Pinecone-Index-Name": st.session_state["pinecone_index_name"],
        "X-Adzuna-App-Id": st.session_state["adzuna_app_id"],
        "X-Adzuna-App-Key": st.session_state["adzuna_app_key"],
        "X-JSearch-Api-Key": st.session_state["jsearch_api_key"],
    }
    return {name: value for name, value in values.items() if value}


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


def _record_event(event: str, payload: dict[str, Any], event_slot: Any, token_slot: Any) -> None:
    if event == "started":
        st.session_state["thread_id"] = payload.get("thread_id", "")
    elif event == "node":
        patch = payload.get("data", {})
        if isinstance(patch, dict):
            for key in RESULT_KEYS:
                if key in patch:
                    if key in {"agent_metrics", "api_metrics"}:
                        merged = dict(st.session_state[key])
                        merged.update(patch[key] or {})
                        st.session_state[key] = merged
                    else:
                        st.session_state[key] = patch[key]
    elif event == "token":
        agent_name = payload.get("agent", "agent")
        current = st.session_state["live_agent_text"].get(agent_name, "")
        current += payload.get("token", "")
        st.session_state["live_agent_text"][agent_name] = current
        token_slot.markdown(f"**{agent_name.replace('_', ' ').title()}**\n\n{current[-4000:]}")
    elif event == "token_reset":
        agent_name = payload.get("agent", "agent")
        st.session_state["live_agent_text"][agent_name] = ""
        token_slot.empty()
    elif event == "interrupt":
        patch = payload.get("data", {})
        if isinstance(patch, dict):
            for key in RESULT_KEYS:
                if key in patch:
                    st.session_state[key] = patch[key]
        st.session_state["pipeline_ready"] = bool(payload.get("artifact_ready"))
        st.session_state["z_axis_approved"] = False
    elif event == "approved":
        st.session_state["z_axis_approved"] = bool(payload.get("z_axis_approved", True))
    elif event == "rpa_result":
        st.session_state["rpa_result"] = payload
    elif event == "error":
        st.session_state["pipeline_error"] = payload.get("status", "Pipeline failed")
        st.session_state["pipeline_ready"] = False

    if event in {"node", "status", "interrupt", "approved", "rpa_result", "error"}:
        if event == "status":
            entry = {"node": payload.get("agent", "Agent"), "status": payload.get("message", "")}
        else:
            entry = {
                "node": payload.get("node", event),
                "status": payload.get("status", payload.get("message", "")),
            }
        st.session_state["pipeline_events"].append(entry)
        with event_slot.container():
            for item in st.session_state["pipeline_events"][-18:]:
                label = str(item["node"]).replace("_", " ").title()
                st.caption(f"{label}  ·  {item['status']}")


def _consume_sse(response: requests.Response, event_slot: Any, token_slot: Any) -> None:
    current_event = "message"
    data_lines: list[str] = []

    def dispatch() -> None:
        nonlocal current_event, data_lines
        if data_lines:
            try:
                payload = json.loads("\n".join(data_lines))
                if isinstance(payload, dict):
                    _record_event(current_event, payload, event_slot, token_slot)
            except json.JSONDecodeError:
                st.session_state["pipeline_error"] = "Backend returned an invalid SSE frame."
        current_event = "message"
        data_lines = []

    for raw_line in response.iter_lines(decode_unicode=True):
        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
        if not line:
            dispatch()
        elif line.startswith("event:"):
            current_event = line.partition(":")[2].strip()
        elif line.startswith("data:"):
            data_lines.append(line.partition(":")[2].lstrip())
    dispatch()


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


def _run_pipeline(role: str, pdf: Any, event_slot: Any, token_slot: Any) -> None:
    _clear_run()
    try:
        with requests.post(
            f"{API_BASE_URL}/run-pipeline",
            data={"target_role": role.strip(), "ats_strictness": st.session_state["ats_strictness"]},
            files={"file": (pdf.name, pdf.getvalue(), "application/pdf")},
            headers=_api_headers(),
            stream=True,
            timeout=(5, 300),
        ) as response:
            response.raise_for_status()
            _consume_sse(response, event_slot, token_slot)
    except requests.RequestException as error:
        details = error.response.text[:600] if error.response is not None else str(error)
        st.session_state["pipeline_error"] = f"CareerOS request failed: {details}"


def _authorize(event_slot: Any, token_slot: Any) -> None:
    thread_id = st.session_state["thread_id"]
    if not thread_id:
        st.error("No active pipeline thread is available.")
        return
    headers = _api_headers()
    headers["X-CareerOS-Thread-ID"] = thread_id
    try:
        with requests.post(
            f"{API_BASE_URL}/approve-z-axis",
            headers=headers,
            stream=True,
            timeout=(5, 300),
        ) as response:
            response.raise_for_status()
            _consume_sse(response, event_slot, token_slot)
    except requests.RequestException as error:
        details = error.response.text[:600] if error.response is not None else str(error)
        st.error(f"Authorization failed: {details}")


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
    sidebar_events = st.empty()
    sidebar_tokens = st.empty()
    if st.button(
        "Authorize Playwright RPA",
        type="primary",
        icon=":material/lock_open:",
        disabled=not st.session_state["pipeline_ready"] or st.session_state["z_axis_approved"],
        key="authorize_rpa",
    ):
        _authorize(sidebar_events, sidebar_tokens)
    if st.session_state["rpa_result"]:
        st.info(st.session_state["rpa_result"].get("message", "Browser preparation complete."))

    st.slider("ATS strictness", min_value=0, max_value=100, key="ats_strictness")
    with st.expander("⚙️ System Credentials", expanded=False):
        st.caption("Credentials are request-scoped and are not stored in the graph or LangSmith traces.")
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
        with st.spinner("Extracting, sourcing, retrieving, and drafting..."):
            _run_pipeline(role, uploaded_pdf, event_output, token_output)
        if st.session_state["pipeline_error"]:
            st.error(st.session_state["pipeline_error"])
        elif st.session_state["pipeline_ready"]:
            st.success("Materials are staged for review. Playwright will not submit the form.")
    elif st.session_state["pipeline_error"]:
        st.error(st.session_state["pipeline_error"])
    if st.session_state["pipeline_events"] and not start:
        with event_output:
            for item in st.session_state["pipeline_events"][-18:]:
                st.caption(f"{str(item['node']).replace('_', ' ').title()} · {item['status']}")
    if st.session_state["live_agent_text"] and not start:
        with token_output:
            for name, text in st.session_state["live_agent_text"].items():
                if text:
                    st.markdown(f"**{name.replace('_', ' ').title()}**\n\n{text[-4000:]}")
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
        cv_path = Path(st.session_state["tailored_cv_path"] or "")
        if cv_path.is_file():
            st.download_button(
                "Download tailored PDF",
                data=cv_path.read_bytes(),
                file_name="tailored-cv.pdf",
                mime="application/pdf",
                icon=":material/download:",
            )
    else:
        st.info("Run the pipeline to create a tailored CV.")

elif navigation == "Job Intelligence":
    _page_header("Workspace / Market", "Job Intelligence", "Live roles gathered from Adzuna and JSearch, normalized and deduplicated.")
    _render_metrics()
    jobs = st.session_state["job_listings"]
    if jobs:
        st.dataframe(
            jobs,
            hide_index=True,
            alt="Live technology roles with employer, location, source, and application link.",
        )
        with st.expander("Provider telemetry"):
            st.json(st.session_state["api_metrics"])
    else:
        st.info("No live listings yet. Run the pipeline from Dynamic Dashboard.")

elif navigation == "Outreach":
    _page_header("Workspace / Communication", "Outreach", "A contextual hiring-manager draft grounded in the profile and selected job.")
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
    if st.session_state["pipeline_events"]:
        st.subheader("Run trace")
        for item in st.session_state["pipeline_events"][-30:]:
            st.markdown(f"`{str(item['node']).replace('_', ' ').title()}` · {item['status']}")