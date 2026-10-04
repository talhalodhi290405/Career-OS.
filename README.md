<div align="center">

# 🚀 CareerOS — Autonomous Digital FTE

**PakAngels Cohort 11 Hackathon | Team CareerOS**

[![Live Demo](https://img.shields.io/badge/Deploy-Live_App-brightgreen?style=for-the-badge&logo=streamlit)](https://career-os-290405.streamlit.app/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js-111111?style=for-the-badge&logo=nextdotjs)](https://nextjs.org/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-4B0082?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)
[![Playwright](https://img.shields.io/badge/RPA-Playwright-2EAD33?style=for-the-badge&logo=playwright)](https://playwright.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

<img src="https://img.shields.io/badge/Status-Deployed_to_Streamlit_Cloud-blue?style=for-the-badge" alt="Status">

> **CareerOS** is a governed career operations workspace. It verifies resume facts, sources live opportunities, generates tailored application materials, and prepares application forms in a visible browser. A human reviews and completes every final submission.

**Product requirements:** See [PRD.md](PRD.md) for the full hackathon requirements, governance model, architecture, demo choreography, and submission checklist.

</div>

---

## 🌟 Product Vision

The modern job seeker spends **200+ hours per year** on repetitive job search tasks — searching boards, tailoring CVs, and writing cold emails. **CareerOS eliminates this entirely.**

CareerOS functions as your autonomous agent: a digital FTE that works 24/7, applies to the right roles, and never acts without your explicit, click-based authorization. It is not just automation — it is **governed agentic intelligence** built on a first-principles Human-in-the-Loop (HITL) framework.

---

## 🏗️ System Architecture

```
Next.js 16 + React 19 control plane (port 3000)
    ├─ same-origin SSE/API proxy
    ├─ X/Y/Z review modules
    └─ request-scoped provider credentials
                                    │
                                    ▼
FastAPI multipart/SSE backend (port 8000) + LangGraph per-run checkpoint
    Gemini/PDF facts ─> Adzuna + JSearch ─> Pinecone RAG ─> Groq CV/letter/outreach/STAR
                                                                                                                │
                                                                                    Z-Axis interrupt / human review
                                                                                                                │
                                                     visible Playwright form preparation (never auto-submits)
```

---

## 🛡️ The X-Y-Z Governance Framework

CareerOS is built on a first-principles Human-in-the-Loop (HITL) governance model. Every axis of the pipeline is accountable:

### X-Axis — Candidate Truth Layer
> **"What is objectively true about the candidate?"**

- Governed by the **Profile Analyzer Agent** using `pdfplumber`, Gemini, Pydantic validation, and source-text checks
- Extracts verifiable facts: top technical skills, years of experience, domain expertise
- Feeds only grounded, factual data to downstream agents — no hallucinations about the candidate's profile are permitted to propagate
- **Constraint**: The Outreach Agent is forbidden from claiming skills not present in the X-Axis fact set

### Y-Axis — Opportunity Matching Layer
> **"What is the best-fit opportunity, and how do we communicate value?"**

- Governed by the **Scout Agent** (Adzuna + JSearch) and Groq-powered content agents
- Scout queries live roles by target role, location, and remote/hybrid/on-site preference
- Outreach Agent tailors the communication to the specific role and company — personalized, not generic
- **Constraint**: All Y-Axis output is staged for review before any action is taken

### Z-Axis — Execution Authorization Gate 🔴
> **"Has a human explicitly consented to this irreversible action?"**

- Governed by a **physical UI button** in the Control Tower panel — this is the critical innovation
- The Playwright RPA agent is **hard-blocked** at the code level (`z_axis_approved: False`) until the button is clicked
- The button remains **disabled** until the full X + Y pipeline completes successfully
- Clicking the button is a **conscious, informed, deliberate act** — not an accidental trigger
- **Constraint**: No application is ever submitted without this explicit human authorization

This framework ensures CareerOS is powerful but never reckless — the system is aggressive in automation but absolute in accountability.

---

## 🤖 Agent Roster

| Agent | Technology | Responsibility |
|---|---|---|
| **Scout** | Adzuna + JSearch REST APIs | Queries and normalizes live roles across location/work modes |
| **Profile Analyzer** | `pdfplumber` + Gemini Flash + Pydantic | Extracts and verifies X-Axis candidate facts from the uploaded resume |
| **RAG** | Pinecone + Gemini embeddings | Stores and retrieves verified candidate facts per run |
| **Tailor / Outreach / Prep** | Groq Llama 3 | Generates a tailored CV, cover letter, outreach, and STAR prompts |
| **RPA Executor** | `playwright.async_api` (visible Chromium) | Fills common fields and attaches a CV, then pauses before submission |

---

## ⚡ Tech Stack

| Layer | Technology |
|---|---|
| **Orchestration** | LangGraph multi-agent state machine |
| **Backend API** | FastAPI with `StreamingResponse` (NDJSON/SSE) |
| **Frontend** | Next.js 16 App Router + React 19 + TypeScript |
| **LLMs** | Gemini Flash for extraction; Groq Llama 3 for tailored content |
| **Vector retrieval** | Pinecone with Gemini embeddings, namespaced by pipeline run |
| **PDF Parsing** | `pdfplumber` |
| **RPA Browser** | Playwright async (visible Chromium; pauses before submit) |
| **Job Discovery** | Adzuna + JSearch |

---

## 🚀 Running Locally

### Prerequisites

- Python 3.11+
- Node.js 22+
- Playwright browsers installed: `playwright install chromium`

### 1. Clone & Install

```bash
git clone https://github.com/talhalodhi290405/Career-OS.git
cd Career-OS
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root (this file is gitignored — never commit it):

```env
# Gemini, Groq, and Pinecone
# GEMINI_API_KEY=...
# GROQ_API_KEY=...
# PINECONE_API_KEY=...
# PINECONE_INDEX_NAME=...
# Adzuna and JSearch
# ADZUNA_APP_ID=...
# ADZUNA_APP_KEY=...
# JSEARCH_API_KEY=...
# TAVILY_API_KEY=...
# RESEND_API_KEY=...
# RESEND_FROM_EMAIL=verified-sender@your-domain.example
# RESEND_WEBHOOK_SECRET=whsec_...
# CAREEROS_EMAIL_LEDGER=./data/email_dispatches.sqlite3
# Backend URL for the Next.js server-side proxy
# CAREEROS_BACKEND_URL=http://127.0.0.1:8000
```

### 3. Place Your Resume

Copy your resume PDF to the project root and name it `resume.pdf`.

### 4. Start the FastAPI Backend

```bash
# In Terminal 1
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

### 5. Start the Next.js Frontend

```bash
cd frontend
npm ci
npm run dev
```

The UI opens at `http://localhost:3000`. The same-origin Next.js API route proxies to `CAREEROS_BACKEND_URL` (default `http://127.0.0.1:8000`).

Create the Pinecone index with the dimension required by the configured Gemini embedding model (`gemini-embedding-001` defaults to 3072 dimensions). Set `PINECONE_INDEX_NAME` and `PINECONE_API_KEY` in the backend environment or enter them in System Credentials.

For Resend delivery, configure a verified `RESEND_FROM_EMAIL`. Point Resend webhooks at `POST /webhooks/resend` and configure its signing secret as `RESEND_WEBHOOK_SECRET`; the endpoint verifies Svix signatures and records delivery/open/click events.

### 6. Using CareerOS

1. Choose a target role, location, and remote/hybrid/on-site mode, then upload a resume.
2. Start the pipeline and watch live agent tokens, provider statuses, and job results.
3. Review verified profile facts, live listings, tailored CV, cover letter, outreach, and interview prompts.
4. Authorize Playwright from the Control Tower to open the application form visibly, fill detected fields, and attach the CV.
5. Review and submit the application yourself; the automation deliberately stops before clicking submit.

---

## 📁 Project Structure

```
Career-OS/
├── main.py            # FastAPI backend — SSE streaming endpoint + RPA trigger
├── agent.py           # LangGraph agents: Profile Analyzer + Outreach
├── rpa_agent.py       # Playwright RPA executor with Z-Axis gate
├── frontend/          # Next.js/React control plane and same-origin API/SSE proxy
├── requirements.txt   # Python dependencies
├── .gitignore         # Excludes .venv, .env, PDFs, __pycache__
├── Dockerfile.backend # Docker config for FastAPI backend
├── Dockerfile.frontend # Docker config for Next.js standalone server
└── .github/
    └── workflows/
        ├── deploy-backend.yml   # CI/CD → Azure Container Apps
        └── deploy-frontend.yml  # CI/CD → Azure Web Apps
```

---

## ☁️ Cloud Deployment

CareerOS is deployed via Streamlit Cloud for the hackathon demo:
👉 **[Live Demo Link](https://career-os-290405.streamlit.app/)**

---

## 👥 Team CareerOS — PakAngels Cohort 11

Built under hackathon conditions in 48 hours. We believe that autonomous AI agents should be **powerful and accountable** — and CareerOS is our proof of concept.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
