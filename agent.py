from __future__ import annotations

import json
import logging
import operator
import os
import re
import time
from pathlib import Path
from typing import Annotated, Any, TypedDict

import pdfplumber
import requests
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_pinecone import PineconeVectorStore
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel, ConfigDict, Field

load_dotenv()
logger = logging.getLogger("careeros.agents")
REQUEST_TIMEOUT = (5, 25)

_langsmith_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"] = "true" if _langsmith_key else "false"
os.environ["LANGSMITH_TRACING"] = "true" if _langsmith_key else "false"
os.environ.setdefault("LANGSMITH_HIDE_INPUTS", "true")
os.environ.setdefault("LANGSMITH_HIDE_OUTPUTS", "true")

class AgentState(TypedDict):
    profile_data: dict[str, Any]
    job_listings: list[dict[str, Any]]
    tailored_cv: str
    tailored_cv_path: str
    cover_letter: str
    outreach_draft: str
    interview_prep: list[str]
    z_axis_approved: bool
    target_role: str
    target_location: str
    workplace_type: str
    target_job_url: str
    resume_pdf_bytes: bytes
    resume_filename: str
    ats_strictness: int
    run_id: str
    agent_metrics: Annotated[dict[str, dict[str, Any]], operator.or_]
    api_metrics: Annotated[dict[str, dict[str, Any]], operator.or_]
    ats_score: int
    company_research: list[dict[str, Any]]
    technical_challenges: list[str]

class CandidateFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    email: str | None = None
    phone: str | None = None
    headline: str
    skills: list[str]
    experience_years: int | None = None
    summary: str
    evidence: list[str] = Field(min_length=1)

class InterviewQuestions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    questions: list[str] = Field(min_length=4, max_length=8)
    technical_challenges: list[str] = Field(min_length=1, max_length=5)

class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verified: bool
    issues: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)

def create_initial_state() -> AgentState:
    return {
        "profile_data": {},
        "job_listings": [],
        "company_research": [],
        "technical_challenges": [],
        "tailored_cv": "",
        "tailored_cv_path": "",
        "cover_letter": "",
        "outreach_draft": "",
        "interview_prep": [],
        "z_axis_approved": False,
        "target_role": "",
        "target_location": "",
        "workplace_type": "Any",
        "target_job_url": "",
        "resume_pdf_bytes": b"",
        "resume_filename": "resume.pdf",
        "ats_strictness": 60,
        "run_id": "",
        "agent_metrics": {},
        "api_metrics": {},
        "ats_score": 0,
    }

def _config_values(config: RunnableConfig) -> dict[str, Any]:
    return config.get("configurable", {})

def _credential(config: RunnableConfig, name: str) -> str:
    value = _config_values(config).get("credentials", {}).get(name)
    if not value:
        value = os.getenv(name)
    if not value and name == "GOOGLE_API_KEY":
        value = os.getenv("GEMINI_API_KEY")
    return str(value).strip() if value else ""

def _writer() -> Any:
    try:
        return get_stream_writer()
    except RuntimeError:
        return lambda _event: None

def _emit(kind: str, **payload: Any) -> None:
    _writer()({"type": kind, **payload})

def _token_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(part.get("text", "")) if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content or "")

def _usage_from_chunk(message: Any) -> dict[str, int]:
    usage = getattr(message, "usage_metadata", None) or {}
    response_meta = getattr(message, "response_metadata", None) or {}
    legacy = response_meta.get("token_usage", {})
    input_tokens = usage.get("input_tokens", legacy.get("prompt_tokens", 0))
    output_tokens = usage.get("output_tokens", legacy.get("completion_tokens", 0))
    return {
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
    }

def _stream_model(
    model: Any,
    node: str,
    messages: list[Any],
    config: RunnableConfig,
) -> tuple[str, dict[str, Any]]:
    started = time.perf_counter()
    pieces: list[str] = []
    usage = {"input_tokens": 0, "output_tokens": 0}
    for chunk in model.stream(messages, config=config):
        text = _token_text(chunk)
        if text:
            pieces.append(text)
            _emit("token", agent=node, token=text)
        chunk_usage = _usage_from_chunk(chunk)
        usage["input_tokens"] = max(usage["input_tokens"], chunk_usage["input_tokens"])
        usage["output_tokens"] = max(usage["output_tokens"], chunk_usage["output_tokens"])
    return "".join(pieces).strip(), {
        **usage,
        "total_tokens": usage["input_tokens"] + usage["output_tokens"],
        "latency_seconds": round(time.perf_counter() - started, 3),
    }

def _parse_json(text: str, schema: type[BaseModel]) -> BaseModel:
    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.I)
    start = value.find("{")
    end = value.rfind("}")
    if start < 0 or end < start:
        raise ValueError("The model did not return a JSON object")
    return schema.model_validate_json(value[start : end + 1])

def _verified_profile(facts: CandidateFacts, resume_text: str) -> dict[str, Any]:
    normalized_resume = re.sub(r"\s+", " ", resume_text).casefold()
    evidence = [
        quote.strip()
        for quote in facts.evidence
        if quote.strip()
        and re.sub(r"\s+", " ", quote).strip().casefold() in normalized_resume
    ]
    if not evidence:
        raise ValueError("Resume facts contained no verifiable evidence quotes")
    name = facts.name.strip()
    normalized_name = re.sub(r"[^\w]+", " ", name, flags=re.UNICODE).strip().casefold()
    resume_name_tokens = set(re.findall(r"\b[\w'-]+\b", normalized_resume, flags=re.UNICODE))
    name_tokens = [token for token in normalized_name.split() if token]
    # Accept normal PDF line/column extraction variations and common full-name/short-name
    # forms while still requiring every supplied name token to be present in the resume.
    name_verified = bool(
        normalized_name
        and (
            normalized_name in normalized_resume
            or (
                len(name_tokens) >= 2
                and all(token in resume_name_tokens for token in name_tokens)
            )
        )
    )
    if not name_verified:
        raise ValueError("Candidate name could not be verified against the resume")
    email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", resume_text, re.I)
    phone_match = re.search(r"(?:\+?\d[\d(). \t-]{7,}\d)", resume_text)
    headline = facts.headline.strip()
    if not headline or re.sub(r"\s+", " ", headline).casefold() not in normalized_resume:
        headline = ""
    experience_match = re.search(r"\b(\d{1,2})\+?\s+years?\b", resume_text, re.I)
    experience_years = facts.experience_years
    if experience_years is not None and (
        experience_match is None or int(experience_match.group(1)) != experience_years
    ):
        experience_years = None
    skills = [
        skill.strip()
        for skill in facts.skills
        if skill.strip() and re.sub(r"\s+", " ", skill).casefold() in normalized_resume
    ]
    return {
        "name": name,
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0).strip() if phone_match else None,
        "headline": headline,
        "skills": skills,
        "experience_years": experience_years,
        "summary": facts.summary.strip(),
        "evidence": evidence,
        "source": "uploaded_pdf",
    }

def _pdf_text(pdf_bytes: bytes) -> str:
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("Uploaded document is not a PDF")
    import io

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages).strip()
    if not text:
        raise ValueError("No selectable text was found in the uploaded PDF")
    return text[:50000]

def _pinecone_store(config: RunnableConfig, namespace: str) -> PineconeVectorStore:
    pinecone_key = _credential(config, "PINECONE_API_KEY")
    google_key = _credential(config, "GOOGLE_API_KEY")
    index_name = (
        _credential(config, "PINECONE_INDEX_NAME")
        or _config_values(config).get("pinecone_index_name")
        or os.getenv("PINECONE_INDEX_NAME")
    )
    if not pinecone_key or not index_name:
        raise RuntimeError("PINECONE_API_KEY and PINECONE_INDEX_NAME are required")
    if not google_key:
        google_key = os.getenv("GEMINI_API_KEY", "")
        if not google_key:
             raise RuntimeError("GOOGLE_API_KEY is required for Gemini embeddings")
    embeddings = GoogleGenerativeAIEmbeddings(
        model=os.getenv("CAREEROS_EMBEDDING_MODEL", "models/gemini-embedding-001"),
        api_key=google_key,
    )
    return PineconeVectorStore(
        index_name=str(index_name),
        embedding=embeddings,
        pinecone_api_key=pinecone_key,
        namespace=namespace,
    )

def profile_analyzer(
    state: AgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    _emit("status", agent="profile_analyzer", message="Extracting resume text and verifying facts with Groq.")
    resume_text = _pdf_text(state["resume_pdf_bytes"])
    groq_key = _credential(config, "GROQ_API_KEY")
    if not groq_key:
        raise RuntimeError("Configure GROQ_API_KEY in the sidebar or backend environment")

    schema = json.dumps(CandidateFacts.model_json_schema(), ensure_ascii=False)
    messages = [
        SystemMessage(
            content=(
                "Extract facts from the resume as JSON matching this schema: "
                f"{schema}. Never invent facts. Include exact verbatim evidence quotes. "
                "Return only JSON."
            )
        ),
        HumanMessage(content=resume_text),
    ]

    model = ChatGroq(
        model="openai/gpt-oss-120b",
        api_key=groq_key,
        temperature=0,
    )

    response_text, metrics = _stream_model(
        model,
        "profile_analyzer",
        messages,
        config,
    )

    if not response_text:
        raise RuntimeError("Groq returned no profile extraction output")
    facts = _parse_json(response_text, CandidateFacts)
    profile = _verified_profile(facts, resume_text)

    namespace = f"careeros-{state['run_id']}"
    vector_store = _pinecone_store(config, namespace)
    fact_text = json.dumps(profile, ensure_ascii=False)
    vector_store.add_documents(
        [Document(page_content=fact_text, metadata={"run_id": state["run_id"], "kind": "verified_profile"})],
        ids=[f"{state['run_id']}-verified-profile"],
    )
    _emit("status", agent="profile_analyzer", message="Verified candidate facts indexed in Pinecone.")
    return {
        "profile_data": profile,
        "agent_metrics": {"profile_analyzer": metrics},
    }

def _remaining_budget(headers: Any) -> int | None:
    for name in (
        "x-ratelimit-remaining",
        "x-ratelimit-requests-remaining",
        "x-rate-limit-remaining",
        "ratelimit-remaining",
    ):
        value = headers.get(name)
        if value and str(value).isdigit():
            return int(value)
    return None

def _normalize_job(
    title: str,
    company: str,
    location: str,
    description: str,
    url: str,
    source: str,
    salary_min: Any = None,
    salary_max: Any = None,
    salary_currency: str | None = None,
    salary_period: str | None = None,
    workplace_type: str | None = None,
) -> dict[str, Any] | None:
    title = title.strip()
    company = company.strip()
    description = description.strip()
    url = url.strip()
    if not title or not company or not description or not url.startswith("https://"):
        return None
    job = {
        "title": title,
        "company": company,
        "location": location.strip() or "Not specified",
        "description": description,
        "url": url,
        "source": source,
    }
    if salary_min is not None or salary_max is not None:
        job["salary_min"] = salary_min
        job["salary_max"] = salary_max
        job["salary_currency"] = salary_currency or "USD"
        job["salary_period"] = salary_period or "year"
    if workplace_type:
        job["workplace_type"] = workplace_type
    return job

def _fetch_adzuna(
    role: str,
    location: str,
    workplace_type: str,
    config: RunnableConfig,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    app_id = _credential(config, "ADZUNA_APP_ID")
    app_key = _credential(config, "ADZUNA_APP_KEY")
    if not app_id or not app_key:
        return [], {"status": "not_configured", "remaining": None, "calls": 0}

    _emit("status", agent="job_scout", message="Querying Adzuna for live job listings.")
    started = time.perf_counter()
    response = None
    try:
        response = requests.get(
            "https://api.adzuna.com/v1/api/jobs/us/search/1",
            params={
                "app_id": app_id,
                "app_key": app_key,
                "what": " ".join(value for value in (role, workplace_type if workplace_type != "Any" else "") if value),
                "where": location,
                "results_per_page": 10,
                "content-type": "application/json",
            },
            timeout=REQUEST_TIMEOUT,
        )
        status = f"http_{response.status_code}"
        response.raise_for_status()
        jobs = [
            job
            for item in response.json().get("results", [])
            if (
                job := _normalize_job(
                    str(item.get("title") or ""),
                    str((item.get("company") or {}).get("display_name") or ""),
                    str((item.get("location") or {}).get("display_name") or ""),
                    str(item.get("description") or ""),
                    str(item.get("redirect_url") or ""),
                    "adzuna",
                    item.get("salary_min"),
                    item.get("salary_max"),
                    item.get("salary_currency"),
                    "estimated" if item.get("salary_is_predicted") else "year",
                    workplace_type,
                )
            )
        ]
        if jobs:
            status = "ok"
        return jobs, {
            "status": status,
            "remaining": _remaining_budget(response.headers),
            "latency_seconds": round(time.perf_counter() - started, 3),
            "calls": 1,
        }
    except (requests.RequestException, ValueError, KeyError) as error:
        logger.warning("Adzuna request failed: %s", type(error).__name__)
        return [], {
            "status": f"http_{response.status_code}" if response is not None else "request_failed",
            "remaining": _remaining_budget(response.headers) if response is not None else None,
            "latency_seconds": round(time.perf_counter() - started, 3),
            "calls": 1,
        }

def _fetch_jsearch(
    role: str,
    location: str,
    workplace_type: str,
    config: RunnableConfig,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    api_key = _credential(config, "JSEARCH_API_KEY")
    if not api_key:
        return [], {"status": "not_configured", "remaining": None, "calls": 0}

    _emit("status", agent="job_scout", message="Querying JSearch for additional live job listings.")
    started = time.perf_counter()
    response = None
    try:
        response = requests.get(
            "https://jsearch.p.rapidapi.com/search",
            params={
                "query": " ".join(
                    value for value in (role, workplace_type if workplace_type != "Any" else "", location) if value
                ) + " jobs",
                "page": "1",
                "num_pages": "1",
            },
            headers={
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
            },
            timeout=REQUEST_TIMEOUT,
        )
        status = f"http_{response.status_code}"
        response.raise_for_status()
        jobs = []
        for item in response.json().get("data", []):
            location = ", ".join(
                str(item.get(field, "")).strip()
                for field in ("job_city", "job_state", "job_country")
                if item.get(field)
            )
            job = _normalize_job(
                str(item.get("job_title") or ""),
                str(item.get("employer_name") or ""),
                location,
                str(item.get("job_description") or ""),
                str(item.get("job_apply_link") or item.get("job_google_link") or ""),
                "jsearch",
                item.get("job_min_salary"),
                item.get("job_max_salary"),
                item.get("job_salary_currency"),
                item.get("job_salary_period"),
                item.get("job_workplace_type") or workplace_type,
            )
            if job:
                jobs.append(job)
        if jobs:
            status = "ok"
        return jobs, {
            "status": status,
            "remaining": _remaining_budget(response.headers),
            "latency_seconds": round(time.perf_counter() - started, 3),
            "calls": 1,
        }
    except (requests.RequestException, ValueError, KeyError) as error:
        logger.warning("JSearch request failed: %s", type(error).__name__)
        return [], {
            "status": f"http_{response.status_code}" if response is not None else "request_failed",
            "remaining": _remaining_budget(response.headers) if response is not None else None,
            "latency_seconds": round(time.perf_counter() - started, 3),
            "calls": 1,
        }

def _fetch_company_research(
    jobs: list[dict[str, Any]],
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    api_key = _credential(config, "TAVILY_API_KEY")
    if not api_key:
        _emit("status", agent="company_research", message="Tavily not configured; live company research is unavailable.")
        return []

    results: list[dict[str, Any]] = []
    for job in jobs:
        _emit("status", agent="company_research", message=f"Researching current public sources for {job['company']}.")
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": f"{job['company']} company news product engineering",
                    "topic": "news",
                    "search_depth": "basic",
                    "max_results": 3,
                    "include_answer": False,
                },
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            items = response.json().get("results", [])
            results.append({
                "company": job["company"],
                "status": "ok" if items else "empty",
                "results": [
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", "")[:900],
                        "published_date": item.get("published_date"),
                    }
                    for item in items
                    if item.get("url") and item.get("content")
                ],
            })
        except (requests.RequestException, ValueError) as error:
            logger.warning("Company research failed for %s: %s", job["company"], type(error).__name__)
            results.append({"company": job["company"], "status": "unavailable", "results": []})
    return results

def job_scout(
    state: AgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    role = state["target_role"]
    location = state.get("target_location", "").strip()
    workplace_type = state.get("workplace_type", "Any")
    has_adzuna = bool(
        _credential(config, "ADZUNA_APP_ID") and _credential(config, "ADZUNA_APP_KEY")
    )
    has_jsearch = bool(_credential(config, "JSEARCH_API_KEY"))
    if not has_adzuna and not has_jsearch:
        raise RuntimeError("Configure Adzuna credentials or JSEARCH_API_KEY to source live jobs")

    started = time.perf_counter()
    adzuna_jobs, adzuna_metrics = _fetch_adzuna(role, location, workplace_type, config)
    jsearch_jobs, jsearch_metrics = _fetch_jsearch(role, location, workplace_type, config)
    jobs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for job in adzuna_jobs + jsearch_jobs:
        identity = job["url"].casefold().rstrip("/") or (
            f"{job['title']}|{job['company']}".casefold()
        )
        if identity not in seen:
            seen.add(identity)
            jobs.append(job)
    if not jobs:
        raise RuntimeError(
            "No live jobs were returned. "
            f"Adzuna: {adzuna_metrics['status']}; JSearch: {jsearch_metrics['status']}"
        )
    verified_skills = [
        skill.strip()
        for skill in (state.get("profile_data") or {}).get("skills", [])
        if isinstance(skill, str) and skill.strip()
    ]
    for job in jobs:
        job_text = f"{job['title']} {job['description']}".casefold()
        matched_skills = [skill for skill in verified_skills if skill.casefold() in job_text]
        job["matched_profile_skills"] = matched_skills
        job["profile_match_pct"] = round(100 * len(matched_skills) / max(len(verified_skills), 1))
    if verified_skills:
        jobs.sort(key=lambda job: job["profile_match_pct"], reverse=True)
    sources = sorted({job["source"] for job in jobs})
    calls = adzuna_metrics.get("calls", 0) + jsearch_metrics.get("calls", 0)
    latency = round(time.perf_counter() - started, 3)
    return {
        "job_listings": jobs[:20],
        "company_research": _fetch_company_research(jobs[:5], config),
        "target_job_url": jobs[0]["url"],
        "api_metrics": {
            "adzuna": adzuna_metrics,
            "jsearch": jsearch_metrics,
            "summary": {"source": "+".join(sources), "calls": calls},
        },
        "agent_metrics": {
            "job_scout": {
                "status": "live_results",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "latency_seconds": latency,
            }
        },
    }

def _retrieve_profile_facts(
    state: AgentState,
    config: RunnableConfig,
    job: dict[str, Any],
) -> str:
    namespace = f"careeros-{state['run_id']}"
    vector_store = _pinecone_store(config, namespace)
    query = (
        f"Verified candidate experience and skills relevant to {job['title']}. "
        f"Job description: {job['description'][:3000]}"
    )
    documents = vector_store.similarity_search(query, k=4)
    if not documents:
        raise RuntimeError("Pinecone returned no verified candidate profile facts")
    return "\n".join(document.page_content for document in documents)

def _groq_model(config: RunnableConfig) -> ChatGroq:
    api_key = _credential(config, "GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Configure GROQ_API_KEY in the sidebar or backend environment")
    return ChatGroq(
        model=os.getenv("CAREEROS_GROQ_MODEL", "openai/gpt-oss-120b"),
        api_key=api_key,
        temperature=0.2,
    )

def tailor_agent(
    state: AgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    job = state["job_listings"][0]
    _emit("status", agent="tailor_agent", message="Retrieving verified profile facts from Pinecone.")
    facts = _retrieve_profile_facts(state, config, job)
    _emit("status", agent="tailor_agent", message="Generating a role-specific CV with Groq.")
    model = _groq_model(config)
    prompt = (
        "Write a concise ATS-readable markdown CV tailored to the job. Use only the "
        "retrieved verified candidate facts. Never invent employers, dates, skills, "
        "metrics, credentials, or responsibilities. Strictness is a 0-100 preference; "
        "higher values require closer evidence and fewer inferred matches.\n\n"
        f"ATS strictness: {state['ats_strictness']}\n"
        f"Retrieved Pinecone facts:\n{facts}\n\n"
        f"Live job:\n{json.dumps(job, ensure_ascii=False)}"
    )
    cv, metrics = _stream_model(
        model,
        "tailor_agent",
        [SystemMessage(content="Create a factual, concise tailored CV."), HumanMessage(content=prompt)],
        config,
    )
    if not cv:
        raise RuntimeError("Groq returned an empty tailored CV")
    _emit("status", agent="tailor_agent", message="Drafting a fact-checked cover letter with Groq.")
    cover_letter_prompt = json.dumps(
        {
            "verified_profile": state["profile_data"],
            "retrieved_verified_facts": facts,
            "job": job,
        },
        ensure_ascii=False,
    )
    cover_letter, cover_letter_metrics = _stream_model(
        model,
        "cover_letter_agent",
        [
            SystemMessage(
                content=(
                    "Write a tailored one-page cover letter for this live job. Use only "
                    "facts present in the verified profile and retrieved facts. Do not "
                    "invent achievements, employers, metrics, or experience. Return polished markdown."
                )
            ),
            HumanMessage(content=cover_letter_prompt),
        ],
        config,
    )
    if not cover_letter:
        raise RuntimeError("Groq returned an empty cover letter")
    profile_skills = state["profile_data"].get("skills", [])
    job_text = f"{job['title']} {job['description']}".casefold()
    matched = [skill for skill in profile_skills if skill.casefold() in job_text]
    score = round(100 * len(matched) / max(len(profile_skills), 1))
    return {
        "tailored_cv": cv,
        "cover_letter": cover_letter,
        "ats_score": score,
        "agent_metrics": {
            "tailor_agent": metrics,
            "cover_letter_agent": cover_letter_metrics,
        },
    }

def outreach_agent(
    state: AgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    job = state["job_listings"][0]
    _emit("status", agent="outreach_agent", message="Drafting contextual outreach with Groq.")
    prompt = json.dumps(
        {
            "verified_profile": state["profile_data"],
            "job": {key: job[key] for key in ("title", "company", "description", "url")},
            "company_research": [
                item for item in state.get("company_research", [])
                if item.get("company") == job.get("company")
            ],
        },
        ensure_ascii=False,
    )
    draft, metrics = _stream_model(
        _groq_model(config),
        "outreach_agent",
        [
            SystemMessage(
                content=(
                    "Draft a concise, professional email to the hiring manager. "
                    "Use only verified candidate facts and this live role. Mention company "
                    "developments only when included in the supplied public research. Do not "
                    "claim an application was submitted. Include a subject line."
                )
            ),
            HumanMessage(content=prompt),
        ],
        config,
    )
    if not draft:
        raise RuntimeError("Groq returned an empty outreach draft")
    return {"outreach_draft": draft, "agent_metrics": {"outreach_agent": metrics}}

def interview_prep_agent(
    state: AgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    job = state["job_listings"][0]
    _emit("status", agent="interview_prep_agent", message="Generating STAR questions with Groq.")
    model = _groq_model(config)
    schema = json.dumps(InterviewQuestions.model_json_schema())
    text, metrics = _stream_model(
        model,
        "interview_prep_agent",
        [
            SystemMessage(
                content=(
                    "Return JSON matching this schema: " + schema + ". Generate 5 "
                    "role-specific behavioral interview questions designed for STAR "
                    "answers plus 2 technical simulation challenges grounded in the job "
                    "description. Use public company research if provided. Do not invent "
                    "candidate experience. Return only JSON."
                )
            ),
            HumanMessage(
                content=json.dumps(
                {
                    "job": job,
                    "verified_profile": state["profile_data"],
                    "company_research": [
                        item for item in state.get("company_research", [])
                        if item.get("company") == job.get("company")
                    ],
                },
                ensure_ascii=False,
                )
            ),
        ],
        config,
    )
    result = _parse_json(text, InterviewQuestions)
    return {
        "interview_prep": result.questions,
        "technical_challenges": result.technical_challenges,
        "agent_metrics": {"interview_prep_agent": metrics},
    }

def z_axis_approval_gate(
    state: AgentState,
    config: RunnableConfig,
) -> dict[str, bool]:
    del config
    if state.get("z_axis_approved") is True:
        return {"z_axis_approved": True}
    approval = interrupt(
        {
            "type": "z_axis_approval_required",
            "message": "Review the generated materials before running Playwright.",
        }
    )
    return {"z_axis_approved": approval is True}

def verification_agent(
    state: AgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    job = state["job_listings"][0]
    _emit("status", agent="verification_agent", message="Performing final Y-Axis truth check for fabrication.")
    model = _groq_model(config)
    verification_prompt = (
        "You are the Y-Axis Truth Guardian. Your sole purpose is to prevent AI hallucinations.\n\n"
        "COMPARE the following tailored materials against the verified candidate profile.\n\n"
        f"VERIFIED PROFILE:\n{json.dumps(state['profile_data'], ensure_ascii=False)}\n\n"
        f"TAILORED CV:\n{state['tailored_cv']}\n\n"
        f"COVER LETTER:\n{state['cover_letter']}\n\n"
        f"OUTREACH DRAFT:\n{state['outreach_draft']}\n\n"
        "RULES:\n"
        "1. If any employer, date, degree, metric, or skill appears in the tailored materials "
        "but is NOT present in the VERIFIED PROFILE, mark as FABRICATED.\n"
        "2. Inferences (e.g., 'experienced in Python' based on a 'Django' project) are allowed "
        "if reasonable, but inventing specific job titles or companies is a critical failure.\n"
        "3. Return JSON: {'verified': bool, 'issues': list[str], 'confidence': float}\n"
        "Return ONLY JSON."
    )
    text, metrics = _stream_model(
        model,
        "verification_agent",
        [SystemMessage(content="You are a strict truth-verification agent. Zero tolerance for fabrication."), HumanMessage(content=verification_prompt)],
        config,
    )
    try:
        result = _parse_json(text, VerificationResult)
        if not result.verified:
            issues = result.issues or ["Fabrication detected in tailored materials."]
            _emit("status", agent="verification_agent", message=f"Fabrication detected: {issues}")
            raise RuntimeError(f"Y-Axis Verification Failed: {issues}")
        _emit("status", agent="verification_agent", message="Materials verified as truthful.")
        return {"agent_metrics": {"verification_agent": metrics}}
    except Exception as e:
        if "Y-Axis Verification Failed" in str(e):
            raise
        logger.exception("Verification agent parsing failed")
        raise RuntimeError("Verification agent crashed while checking for hallucinations")

def rpa_submission_node(
    state: AgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    _emit("status", agent="rpa_agent", message="Submitting application via cloud demo simulation...")
    return {"application_status": "Simulated Success for Cloud Demo"}

def _approval_route(state: AgentState) -> str:
    if state.get("z_axis_approved") is True:
        return "approved"
    return "approval_required"

_builder = StateGraph(AgentState)
_builder.add_node("profile_analyzer", profile_analyzer)
_builder.add_node("job_scout", job_scout)
_builder.add_node("tailor_agent", tailor_agent)
_builder.add_node("outreach_agent", outreach_agent)
_builder.add_node("interview_prep_agent", interview_prep_agent)
_builder.add_node("z_axis_approval_gate", z_axis_approval_gate)
_builder.add_edge(START, "profile_analyzer")
_builder.add_edge("profile_analyzer", "job_scout")
_builder.add_edge("job_scout", "tailor_agent")
_builder.add_edge("tailor_agent", "outreach_agent")
_builder.add_edge("outreach_agent", "interview_prep_agent")
_builder.add_conditional_edges(
    "interview_prep_agent",
    _approval_route,
    {"approved": END, "approval_required": "z_axis_approval_gate"},
)
_builder.add_edge("z_axis_approval_gate", END)

careeros_graph = _builder.compile(checkpointer=InMemorySaver())
