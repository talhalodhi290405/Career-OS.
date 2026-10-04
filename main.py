from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import requests
import sqlite3
import tempfile
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import closing
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.tracers import LangChainTracer
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from agent import AgentState, careeros_graph, create_initial_state
from rpa_agent import run_application_bot


load_dotenv()
_langsmith_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"] = "true" if _langsmith_key else "false"
os.environ["LANGSMITH_TRACING"] = "true" if _langsmith_key else "false"
os.environ.setdefault("LANGSMITH_HIDE_INPUTS", "true")
os.environ.setdefault("LANGSMITH_HIDE_OUTPUTS", "true")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("careeros.backend")
app = FastAPI(title="CareerOS Streaming Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_RESUME_BYTES = 12 * 1024 * 1024
ARTIFACT_DIRECTORY = Path(
    os.getenv("CAREEROS_ARTIFACT_DIRECTORY", Path(tempfile.gettempdir()) / "careeros-artifacts")
)
EMAIL_LEDGER_PATH = Path(
    os.getenv("CAREEROS_EMAIL_LEDGER", str(ARTIFACT_DIRECTORY / "email_dispatches.sqlite3"))
)


def _sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False, default=_json_default)}\n\n"


def _json_default(value: Any) -> Any:
    if isinstance(value, bytes):
        return "[redacted binary payload]"
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "__dict__"):
        return vars(value)
    return str(value)


def _run_config(thread_id: str, credentials: dict[str, str], index_name: str, target_role: str) -> dict[str, Any]:
    configurable: dict[str, Any] = {
        "thread_id": thread_id,
        "credentials": credentials,
        "pinecone_index_name": index_name,
    }
    config: dict[str, Any] = {
        "configurable": configurable,
        "metadata": {"application": "careeros", "target_role": target_role},
        "tags": ["careeros", "digital-fte"],
    }
    if _langsmith_key:
        config["callbacks"] = [
            LangChainTracer(project_name=os.getenv("LANGCHAIN_PROJECT", "careeros-digital-fte"))
        ]
    return config


def _credentials_from_request(request: Request) -> dict[str, str]:
    names = {
        "GOOGLE_API_KEY": "x-google-api-key",
        "GROQ_API_KEY": "x-groq-api-key",
        "PINECONE_API_KEY": "x-pinecone-api-key",
        "ADZUNA_APP_ID": "x-adzuna-app-id",
        "ADZUNA_APP_KEY": "x-adzuna-app-key",
        "JSEARCH_API_KEY": "x-jsearch-api-key",
        "TAVILY_API_KEY": "x-tavily-api-key",
        "RESEND_API_KEY": "x-resend-api-key",
        "TAVILY_API_KEY": "x-tavily-api-key",
        "RESEND_API_KEY": "x-resend-api-key",
    }
    return {
        name: request.headers.get(header, "").strip() or os.getenv(name, "").strip()
        for name, header in names.items()
    }


class OutreachSendRequest(BaseModel):
    thread_id: str = Field(min_length=16, max_length=64)
    recipient_email: str = Field(min_length=5, max_length=254)
    consent: bool = False
    daily_email_limit: int = Field(default=5, ge=0, le=50)


def _reserve_daily_email(thread_id: str, recipient_email: str, daily_limit: int) -> str:
    if daily_limit < 1:
        raise HTTPException(status_code=429, detail="Daily email sending is disabled by the current limit.")
    EMAIL_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    dispatch_id = uuid.uuid4().hex
    day = datetime.now(timezone.utc).date().isoformat()
    recipient_hash = hashlib.sha256(recipient_email.strip().casefold().encode("utf-8")).hexdigest()
    with closing(sqlite3.connect(EMAIL_LEDGER_PATH, timeout=15, isolation_level=None)) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS outreach_dispatches ("
            "dispatch_id TEXT PRIMARY KEY, day TEXT NOT NULL, run_id TEXT NOT NULL, "
            "recipient_hash TEXT NOT NULL, status TEXT NOT NULL, provider_id TEXT, created_at TEXT NOT NULL)"
        )
        connection.execute("BEGIN IMMEDIATE")
        sent_today = connection.execute(
            "SELECT COUNT(*) FROM outreach_dispatches WHERE day = ? AND status IN ('reserved', 'sent')",
            (day,),
        ).fetchone()[0]
        if sent_today >= daily_limit:
            connection.execute("ROLLBACK")
            raise HTTPException(status_code=429, detail="Daily outreach limit reached.")
        connection.execute(
            "INSERT INTO outreach_dispatches "
            "(dispatch_id, day, run_id, recipient_hash, status, created_at) "
            "VALUES (?, ?, ?, ?, 'reserved', ?)",
            (dispatch_id, day, thread_id, recipient_hash, datetime.now(timezone.utc).isoformat()),
        )
        connection.execute("COMMIT")
    return dispatch_id


def _finish_email_dispatch(dispatch_id: str, status: str, provider_id: str | None = None) -> None:
    with closing(sqlite3.connect(EMAIL_LEDGER_PATH, timeout=15, isolation_level=None)) as connection:
        connection.execute(
            "UPDATE outreach_dispatches SET status = ?, provider_id = ? WHERE dispatch_id = ?",
            (status, provider_id, dispatch_id),
        )


def _create_tailored_cv_pdf(markdown: str, run_id: str) -> Path:
    ARTIFACT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_DIRECTORY / f"tailored-cv-{run_id}.pdf"
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CareerOSTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=17, leading=21, alignment=TA_CENTER,
        textColor=colors.HexColor("#33252A"), spaceAfter=8,
    )
    heading_style = ParagraphStyle(
        "CareerOSHeading", parent=styles["Heading2"], fontSize=11,
        leading=14, textColor=colors.HexColor("#8B1E3F"), spaceBefore=8, spaceAfter=3,
    )
    body_style = ParagraphStyle(
        "CareerOSBody", parent=styles["BodyText"], fontSize=9, leading=12, spaceAfter=4,
    )
    document = SimpleDocTemplate(
        str(path), pagesize=letter, rightMargin=48, leftMargin=48,
        topMargin=42, bottomMargin=42, title="Tailored CareerOS CV",
    )
    story = []
    for raw_line in markdown.splitlines():
        line = re.sub(r"\*\*(.*?)\*\*", r"\1", raw_line.strip())
        if not line:
            story.append(Spacer(1, 3))
        elif line.startswith("# "):
            story.append(Paragraph(escape(line[2:]), title_style))
            story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#FF3131")))
        elif line.startswith("## "):
            story.append(Paragraph(escape(line[3:]), heading_style))
        else:
            text = "&#8226; " + escape(line[2:]) if line.startswith(("- ", "* ")) else escape(line)
            story.append(Paragraph(text, body_style))
    document.build(story)
    return path


def _status_for_node(node: str) -> str:
    return {
        "profile_analyzer": "Profile facts verified and indexed.",
        "job_scout": "Live job sourcing complete.",
        "tailor_agent": "Tailored CV generated.",
        "outreach_agent": "Outreach draft generated.",
        "interview_prep_agent": "STAR interview questions generated.",
    }.get(node, node.replace("_", " ").title())


async def _stream_graph(
    initial_state: AgentState | None,
    config: dict[str, Any],
    thread_id: str,
) -> AsyncIterator[str]:
    try:
        async for mode, chunk in careeros_graph.astream(
            initial_state,
            config=config,
            stream_mode=["updates", "custom"],
        ):
            if mode == "custom":
                kind = chunk.get("type", "status")
                yield _sse(kind, chunk)
                continue

            for node, state_update in chunk.items():
                if node == "__interrupt__":
                    snapshot = careeros_graph.get_state(config)
                    markdown = str(snapshot.values.get("tailored_cv", ""))
                    if not markdown:
                        yield _sse("error", {"status": "No tailored CV was generated."})
                        return
                    cv_path = _create_tailored_cv_pdf(markdown, thread_id)
                    careeros_graph.update_state(config, {"tailored_cv_path": str(cv_path)})
                    interrupt_values = [
                        getattr(item, "value", item) for item in state_update
                    ] if isinstance(state_update, tuple) else [state_update]
                    yield _sse(
                        "interrupt",
                        {
                            "node": node,
                            "status": "Review the generated materials before authorizing Playwright.",
                            "data": {
                                "z_axis_approved": False,
                                "tailored_cv_path": str(cv_path),
                                "interrupt": interrupt_values,
                            },
                            "artifact_ready": True,
                        },
                    )
                else:
                    yield _sse(
                        "node",
                        {"node": node, "status": _status_for_node(node), "data": state_update},
                    )
        yield _sse("complete", {"status": "Graph paused for approval or completed."})
    except asyncio.CancelledError:
        raise
    except Exception as error:
        logger.exception("CareerOS graph execution failed")
        yield _sse("error", {"status": str(error)})


@app.get("/")
async def health_check() -> dict[str, str]:
    return {"status": "CareerOS backend active"}


@app.post("/run-pipeline")
async def run_pipeline(
    request: Request,
    target_role: str = Form(..., min_length=1, max_length=120),
    target_location: str = Form("", max_length=160),
    workplace_type: str = Form("Any", pattern="^(Any|Remote|Hybrid|On-site)$"),
    ats_strictness: int = Form(60, ge=0, le=100),
    file: UploadFile = File(...),
) -> StreamingResponse:
    role = target_role.strip()
    if not role:
        raise HTTPException(status_code=422, detail="Target role cannot be blank")
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="Upload a PDF resume")
    pdf_bytes = await file.read(MAX_RESUME_BYTES + 1)
    await file.close()
    if len(pdf_bytes) > MAX_RESUME_BYTES:
        raise HTTPException(status_code=413, detail="Resume exceeds the 12 MiB limit")
    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="Uploaded file is not a valid PDF")

    thread_id = uuid.uuid4().hex
    credentials = _credentials_from_request(request)
    index_name = request.headers.get("x-pinecone-index-name", "").strip() or os.getenv(
        "PINECONE_INDEX_NAME", ""
    )
    config = _run_config(thread_id, credentials, index_name, role)
    initial_state = create_initial_state()
    initial_state.update(
        {
            "target_role": role,
            "target_location": target_location.strip(),
            "workplace_type": workplace_type,
            "resume_pdf_bytes": pdf_bytes,
            "resume_filename": Path(file.filename or "resume.pdf").name,
            "ats_strictness": ats_strictness,
            "run_id": thread_id,
        }
    )

    async def event_stream() -> AsyncIterator[str]:
        yield _sse("started", {"thread_id": thread_id, "target_role": role})
        async for event in _stream_graph(initial_state, config, thread_id):
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/approve-z-axis")
async def approve_z_axis(
    request: Request,
    x_careeros_thread_id: str = Header(...),
) -> StreamingResponse:
    thread_id = x_careeros_thread_id.strip()
    config = _run_config(
        thread_id,
        _credentials_from_request(request),
        request.headers.get("x-pinecone-index-name", "").strip()
        or os.getenv("PINECONE_INDEX_NAME", ""),
        "",
    )
    snapshot = careeros_graph.get_state(config)
    if not snapshot.values or "z_axis_approval_gate" not in snapshot.next:
        raise HTTPException(status_code=409, detail="This run is not waiting for Z-Axis approval")
    if not snapshot.values.get("tailored_cv_path"):
        raise HTTPException(status_code=409, detail="Tailored CV artifact is unavailable")
    careeros_graph.update_state(config, {"z_axis_approved": True})
    if careeros_graph.get_state(config).values.get("z_axis_approved") is not True:
        raise HTTPException(status_code=409, detail="Approval could not be recorded")

    async def event_stream() -> AsyncIterator[str]:
        yield _sse("approved", {"status": "Human approval recorded.", "z_axis_approved": True})
        async for event in _stream_graph(None, config, thread_id):
            yield event
        state = careeros_graph.get_state(config).values
        if state.get("z_axis_approved") is not True:
            yield _sse("rpa_result", {"rpa_status": "blocked", "message": "Approval gate did not complete."})
            return
        result = await run_application_bot(
            str(state["tailored_cv_path"]),
            str(state["target_job_url"]),
            candidate_name=str((state.get("profile_data") or {}).get("name", "")),
            candidate_email=str((state.get("profile_data") or {}).get("email") or ""),
            z_axis_approved=True,
        )
        yield _sse("rpa_result", result)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/send-outreach")
async def send_outreach(payload: OutreachSendRequest, request: Request) -> dict[str, Any]:
    if payload.consent is not True:
        raise HTTPException(status_code=403, detail="Explicit consent is required to send outreach.")
    recipient = payload.recipient_email.strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", recipient):
        raise HTTPException(status_code=422, detail="Enter a valid recipient email address.")

    credentials = _credentials_from_request(request)
    api_key = credentials.get("RESEND_API_KEY", "")
    sender = request.headers.get("x-resend-from-email", "").strip() or os.getenv("RESEND_FROM_EMAIL", "").strip()
    if not api_key or not sender:
        raise HTTPException(
            status_code=503,
            detail="Resend API key and a verified RESEND_FROM_EMAIL are required.",
        )

    config = _run_config(payload.thread_id, credentials, "", "")
    snapshot = careeros_graph.get_state(config)
    if not snapshot.values or not snapshot.values.get("outreach_draft"):
        raise HTTPException(status_code=409, detail="This pipeline has no outreach draft to send.")

    dispatch_id = _reserve_daily_email(
        payload.thread_id,
        recipient,
        payload.daily_email_limit,
    )
    draft = str(snapshot.values["outreach_draft"]).strip()
    subject_match = re.search(r"(?im)^subject:\s*(.+)$", draft)
    subject = subject_match.group(1).strip() if subject_match else "Career opportunity"
    body = re.sub(r"(?im)^subject:\s*.+\n?", "", draft, count=1).strip()
    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"from": sender, "to": [recipient], "subject": subject, "text": body},
            timeout=(5, 20),
        )
        response.raise_for_status()
        provider_id = str(response.json().get("id", ""))
    except (requests.RequestException, ValueError) as error:
        _finish_email_dispatch(dispatch_id, "failed")
        status = getattr(getattr(error, "response", None), "status_code", None)
        logger.warning("Resend dispatch failed with status %s", status or "network_error")
        raise HTTPException(
            status_code=502,
            detail=f"Resend did not accept the email (HTTP {status or 'network error'}).",
        ) from error

    _finish_email_dispatch(dispatch_id, "sent", provider_id)
    return {
        "status": "sent",
        "provider_id": provider_id,
        "message": "Outreach email sent after explicit human consent.",
        "daily_limit": payload.daily_email_limit,
    }


@app.post("/webhooks/resend")
async def resend_webhook(request: Request) -> dict[str, str]:
    webhook_secret = os.getenv("RESEND_WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="Resend webhook verification is not configured.")
    webhook_id = request.headers.get("svix-id", "")
    timestamp = request.headers.get("svix-timestamp", "")
    signatures = request.headers.get("svix-signature", "")
    body = await request.body()
    try:
        timestamp_number = int(timestamp)
        secret_value = webhook_secret.removeprefix("whsec_")
        signing_key = base64.b64decode(secret_value, validate=True)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature metadata.") from None
    if abs(time.time() - timestamp_number) > 300:
        raise HTTPException(status_code=400, detail="Webhook timestamp is outside the allowed window.")
    signed_content = webhook_id.encode() + b"." + timestamp.encode() + b"." + body
    expected = base64.b64encode(hmac.new(signing_key, signed_content, hashlib.sha256).digest()).decode()
    if not any(
        version == "v1" and hmac.compare_digest(signature, expected)
        for candidate in signatures.split()
        if (parts := candidate.split(",", maxsplit=1)) and len(parts) == 2
        for version, signature in [parts]
    ):
        raise HTTPException(status_code=401, detail="Webhook signature verification failed.")
    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid webhook JSON.") from None

    event_type = str(event.get("type", ""))
    data = event.get("data") or {}
    provider_id = str(data.get("email_id") or data.get("id") or "")
    if event_type not in {
        "email.sent",
        "email.delivered",
        "email.opened",
        "email.clicked",
        "email.bounced",
        "email.complained",
    } or not provider_id:
        raise HTTPException(status_code=400, detail="Unsupported or incomplete Resend event.")

    EMAIL_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(EMAIL_LEDGER_PATH, timeout=15, isolation_level=None)) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS outreach_events ("
            "event_id TEXT PRIMARY KEY, provider_id TEXT NOT NULL, "
            "event_type TEXT NOT NULL, occurred_at TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT OR IGNORE INTO outreach_events (event_id, provider_id, event_type, occurred_at) "
            "VALUES (?, ?, ?, ?)",
            (webhook_id, provider_id, event_type, datetime.now(timezone.utc).isoformat()),
        )
    return {"status": "recorded"}


@app.get("/outreach-analytics")
async def outreach_analytics(
    x_careeros_thread_id: str = Header(...),
) -> dict[str, Any]:
    thread_id = x_careeros_thread_id.strip()
    if not EMAIL_LEDGER_PATH.is_file():
        return {"sent": 0, "delivered": 0, "opened": 0, "clicked": 0, "bounced": 0}
    with closing(sqlite3.connect(EMAIL_LEDGER_PATH, timeout=10)) as connection:
        sent = connection.execute(
            "SELECT COUNT(*) FROM outreach_dispatches WHERE run_id = ? AND status = 'sent'",
            (thread_id,),
        ).fetchone()[0]
        try:
            rows = connection.execute(
                "SELECT e.event_type, COUNT(*) FROM outreach_events e "
                "JOIN outreach_dispatches d ON d.provider_id = e.provider_id "
                "WHERE d.run_id = ? GROUP BY e.event_type",
                (thread_id,),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
    events = {name: count for name, count in rows}
    return {
        "sent": sent,
        "delivered": events.get("email.delivered", 0),
        "opened": events.get("email.opened", 0),
        "clicked": events.get("email.clicked", 0),
        "bounced": events.get("email.bounced", 0),
    }