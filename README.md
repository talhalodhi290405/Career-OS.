<div align="center">

# 🚀 CareerOS — Autonomous Digital FTE

**PakAngels Cohort 11 Hackathon | Team CareerOS**

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit)](https://streamlit.io/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-4B0082?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)
[![Playwright](https://img.shields.io/badge/RPA-Playwright-2EAD33?style=for-the-badge&logo=playwright)](https://playwright.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

> **CareerOS** is the world's first Autonomous Digital Full-Time Employee (FTE) for job acquisition — a self-operating AI system that scouts live remote roles, analyzes your profile, drafts personalized outreach, and physically submits applications through a governed RPA pipeline, all under strict human oversight.

</div>

---

## 🌟 Product Vision

The modern job seeker spends **200+ hours per year** on repetitive job search tasks — searching boards, tailoring CVs, and writing cold emails. **CareerOS eliminates this entirely.**

CareerOS functions as your autonomous agent: a digital FTE that works 24/7, applies to the right roles, and never acts without your explicit, click-based authorization. It is not just automation — it is **governed agentic intelligence** built on a first-principles Human-in-the-Loop (HITL) framework.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CAREEROS PIPELINE                           │
│                                                                 │
│  ┌──────────┐    ┌───────────┐    ┌──────────┐    ┌─────────┐  │
│  │  Scout   │───▶│ Analyzer  │───▶│ Outreach │───▶│  RPA    │  │
│  │  Agent   │    │  Agent    │    │  Agent   │    │  Agent  │  │
│  │ (X-Axis) │    │ (X-Axis)  │    │ (Y-Axis) │    │(Z-Axis) │  │
│  └──────────┘    └───────────┘    └──────────┘    └────┬────┘  │
│  Remotive API    pdfplumber +      Local Llama 3   Playwright  │
│                  Local Llama 3                      (Blocked)  │
│                                                         │       │
│                                              ┌──────────▼────┐  │
│                                              │  Z-AXIS GATE  │  │
│                                              │ Human Approval│  │
│                                              │  Required ⚠️  │  │
│                                              └───────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                                        │
   FastAPI (SSE)                           Streamlit UI
   Port 8000                               Port 8501
```

---

## 🛡️ The X-Y-Z Governance Framework

CareerOS is built on a first-principles Human-in-the-Loop (HITL) governance model. Every axis of the pipeline is accountable:

### X-Axis — Candidate Truth Layer
> **"What is objectively true about the candidate?"**

- Governed by the **Profile Analyzer Agent** using `pdfplumber` + local **Llama 3**
- Extracts verifiable facts: top technical skills, years of experience, domain expertise
- Feeds only grounded, factual data to downstream agents — no hallucinations about the candidate's profile are permitted to propagate
- **Constraint**: The Outreach Agent is forbidden from claiming skills not present in the X-Axis fact set

### Y-Axis — Opportunity Matching Layer
> **"What is the best-fit opportunity, and how do we communicate value?"**

- Governed by the **Scout Agent** (live Remotive API) + **Outreach Agent** (Llama 3)
- Scout queries live remote job boards and returns ranked, real opportunities
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
| **Scout** | Remotive REST API + `httpx` | Queries live remote job board, returns top 3 ranked matches |
| **Profile Analyzer** | `pdfplumber` + local Llama 3 (via Ollama) | Extracts X-Axis candidate facts from uploaded PDF resume |
| **Outreach** | Local Llama 3 (via Ollama) | Drafts Y-Axis personalized cold outreach email per role |
| **RPA Executor** | `playwright` (async headless Chromium) | Navigates job portal DOM, fills fields, uploads PDF, submits |

---

## ⚡ Tech Stack

| Layer | Technology |
|---|---|
| **Orchestration** | LangGraph multi-agent state machine |
| **Backend API** | FastAPI with `StreamingResponse` (NDJSON/SSE) |
| **Frontend** | Streamlit with native containers and live streaming |
| **LLM** | Local Llama 3 via Ollama (zero API cost, full privacy) |
| **PDF Parsing** | `pdfplumber` |
| **RPA Browser** | Playwright async (headless Chromium) |
| **Job Discovery** | Remotive public API |

---

## 🚀 Running Locally

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai/) installed with `llama3` model pulled: `ollama pull llama3`
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
# Optional: Only needed if using cloud LLM providers instead of local Ollama
# GROQ_API_KEY=your_key_here
# GOOGLE_API_KEY=your_key_here
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

### 5. Start the Streamlit Frontend

```bash
# In Terminal 2
streamlit run app.py
```

The UI will open at `http://localhost:8501`.

### 6. Using CareerOS

1. Enter your target role (e.g., `"AI Engineer"`, `"Python Developer"`)
2. Click **"Fire Autonomous Pipeline"** — watch the live SSE stream as each agent activates
3. Review the Scout's live job intelligence, the Analyzer's X-Axis profile facts, and the Outreach draft
4. When the pipeline completes, the **"Authorize Playwright RPA"** button activates in the **Control Tower**
5. Click to grant Z-Axis approval — the headless browser launches and submits your application

---

## 📁 Project Structure

```
Career-OS/
├── main.py            # FastAPI backend — SSE streaming endpoint + RPA trigger
├── agent.py           # LangGraph agents: Profile Analyzer + Outreach
├── rpa_agent.py       # Playwright RPA executor with Z-Axis gate
├── app.py             # Streamlit frontend — live dashboard + Control Tower
├── requirements.txt   # Python dependencies
├── .gitignore         # Excludes .venv, .env, PDFs, __pycache__
├── Dockerfile.backend # Docker config for FastAPI backend
├── Dockerfile.frontend # Docker config for Streamlit UI
└── .github/
    └── workflows/
        ├── deploy-backend.yml   # CI/CD → Azure Container Apps
        └── deploy-frontend.yml  # CI/CD → Azure Web Apps
```

---

## ☁️ Cloud Deployment (Azure)

CareerOS is configured for automated CI/CD deployment via GitHub Actions:

- **Backend (FastAPI)** → Azure Container Apps (serverless, scales to zero)
- **Frontend (Streamlit)** → Azure Web Apps (always-on, custom domain ready)

See `.github/workflows/` for the full CI/CD pipeline configuration.

Required GitHub Secrets:

| Secret | Description |
|---|---|
| `AZURE_CREDENTIALS` | Azure Service Principal JSON |
| `REGISTRY_LOGIN_SERVER` | Azure Container Registry URL |
| `REGISTRY_USERNAME` | ACR username |
| `REGISTRY_PASSWORD` | ACR password |
| `AZURE_WEBAPP_PUBLISH_PROFILE` | Azure Web App publish profile XML |

---

## 👥 Team CareerOS — PakAngels Cohort 11

Built under hackathon conditions in 48 hours. We believe that autonomous AI agents should be **powerful and accountable** — and CareerOS is our proof of concept.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
