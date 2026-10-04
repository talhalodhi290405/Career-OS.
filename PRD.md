# CAREERBRIDGE AI / CAREEROS
## PRODUCT REQUIREMENTS

**Product:** CareerBridge AI / CareerOS - Autonomous Job Acquisition Digital FTE
**Program:** PakAngels Cohort 11 Generative & Agentic AI Hackathon
**Phase:** Final Hackathon Deployment (Advanced MVP)
**Team:** 6-Member Engineering Team | Lead: Talha Lodhi

**Document purpose**
A hackathon-ready Product Requirements Document defining the product vision, governance model, agentic architecture, integration ecosystem, cloud stack, interface modules, and 48-hour execution plan for CareerOS. Prepared for engineering, demo choreography, and final submission.

**CORE DESIGN PRINCIPLE** 
CareerOS is positioned as an active Digital FTE: it discovers opportunities, prepares application artifacts, orchestrates execution, and exposes every consequential action to human approval.

---

### 01 Executive Summary & Product Vision
CareerBridge Al operates as CareerOS, an autonomous, enterprise-grade Digital Full-Time Equivalent designed for automated job acquisition. The product evolves beyond passive resume optimization by combining live job intelligence, RAG-based personalization, browser automation, and governed outreach inside one orchestrated workflow.

**PRODUCT THESIS** 
Move the candidate from "search and apply manually" to a governed, observable agent loop: Scout -> Understand -> Tailor -> Review -> Execute -> Learn.

**Primary Product Capabilities**
* Continuously scout live job markets and aggregate high-match opportunities based on role and location parameters.
* Tailor application materials using verified candidate history and job-specific requirements, while blocking unsupported claims.
* Draft personalized hiring-manager outreach grounded in company developments and verified candidate strengths.
* Execute browser-based application workflows only after explicit human approval.
* Prepare company-specific interview scenarios and technical practice matched to live applications.
* Expose real-time agent state, approvals, API budgets, and application artifacts through a TypeScript control interface.

### 02 Problem Statement & Market Friction
**The ATS Black Hole**
The product frames ATS screening as a major source of candidate friction, where keyword or formatting mismatches can prevent qualified applicants from reaching human review. The PRD cites rejection rates of up to 75% as the problem framing used for the hackathon narrative.

**AI Compliance Liabilities**
Unconstrained generative systems can fabricate professional experience, skills, or credentials. CareerOS therefore treats factual integrity as an architectural control, not a prompt-writing preference.

**Workflow Fragmentation**
Candidates commonly move between job boards, resume editors, email tools, and employer portals. This fragmented workflow creates duplicated effort, inconsistent application artifacts, and weak end-to-end analytics.

### 03 Core Governance: HITL X-Y-Z Framework

**X-Axis - Extract & Verify**
* A 7-stage security pipeline extracts foundational user facts from the source PDF using pdfplumber.
* Pydantic schemas validate the extracted structure before information is treated as a trusted profile fact.
* Verified facts are locked into the vector retrieval layer so downstream agents operate against an approved source of truth.

**Y-Axis - Yield & Guardrails**
* Strict Natural Language Inference (NLI) rules constrain tailoring and prevent the injection of unverified skills or synthetic professional data.
* The tailoring agent must align generated claims with retrieved, verified profile evidence and the target job description.

**Z-Axis - Zero-Error Approval**
* A split-screen review interface requires explicit human sign-off before any tailored CV is saved as a final artifact.
* Outreach remains staged until approval authorizes dispatch.
* Automated browser actions remain gated until the human explicitly approves execution.

**GOVERNANCE OUTCOME** 
The system separates generation from execution. Agents may prepare actions autonomously, but consequential external actions remain under explicit human control.

### 04 Multi-Agent Orchestration: LangGraph Engine
* **Profile Analyzer Agent:** Ingest PDF; chunk content; extract and verify facts; embed approved skills into Pinecone.
* **Job Intelligence / Scout Agent:** Query real-time job APIs and aggregate opportunities using role and location parameters.
* **Matching & Personalization / Tailor Agent:** Use RAG to align verified candidate history with target job descriptions and generate distinct tailored CV versions.
* **Outreach Agent:** Draft personalized cold emails using company developments and the candidate's verified capabilities; hold dispatch behind HITL approval.
* **Interview Prep Agent:** Generate company-specific STAR behavioral scenarios and technical simulation challenges from the targeted job description.

### 05 Agentic Automation & API Ecosystem
* **Live Sourcing:** JSearch, Tavily, Remotive, Adzuna (Real-time discovery and aggregation of relevant vacancies).
* **Email Dispatch & Analytics:** Resend API or authenticated Gmail AΡΙ (HITL-approved outbound email with open/click analytics where supported).
* **Autonomous Application (RPA):** Python Playwright + LangGraph (Headless browser navigates target portals, maps DOM fields, uploads tailored PDF, and submits only after Z-Axis approval).
* **EXECUTION BOUNDARY:** Browser automation is not a free-running agent. The LangGraph trigger is treated as an execution request that is blocked unless the Z-Axis approval state is true.

### 06 Enterprise Cloud & Technology Stack
* **Frontend UI:** TypeScript, React / Next.js (Type-safe dynamic Lovable components with native Dark and Light modes).
* **Backend Core:** Python, FastAPI, LangGraph (Async task dispatching plus WebSocket/SSE streaming for real-time UI rendering).
* **Hybrid AI Engine:** Google Gemini 1.5 Flash + Groq (Llama 3). Gemini for heavy document context / structured extraction; Groq for rapid inference.
* **Live Job Sourcing:** Remotive + Adzuna (Remote technology listings and localized / salary-benchmarked vacancies).
* **Vector Database:** Pinecone Serverless (Managed vector storage with native LangChain integration).
* **Dev Environment:** JetBrains Ecosystem (PyCharm Professional, WebStorm, and DataGrip).
* **Cloud Hosting:** Microsoft Azure (Azure Static Web Apps for UI; Azure Container Apps for backend; GitHub Actions for CI/CD).

### 07 CareerOS Interface Modules
* **Dynamic Dashboard:** Visualizes the Live Agent Workflow, agent execution states, and token usage.
* **CV Versions Hub:** Displays tailored resume versions for target companies together with calculated ATS match scores.
* **Job Intelligence Board:** Highlights curated market insights, competitor analysis, and salary benchmark updates.
* **Outreach Automation:** Stages personalized emails behind the Z-Axis approval gate; no dispatch occurs before human consent.
* **Interview Prep Center:** Organizes company-specific behavioral questions and technical coding challenges linked to live applications.
* **Control Tower & Settings:** Provides Daily Email Limits, API Budget Limits, ATS Strictness controls, and secure credential entry.

### 08 48-Hour Master Execution & Submission Timeline
* **PHASE 1 (HOURS 0-6): Foundation & Cloud Setup** - Initialize GitHub repository: create.env.example; provision Azure Static Web Apps and Azure Container Apps; configure GitHub Actions CICD.
* **PHASE 2 (HOURS 6-20): Agentic Engine & UI Rendering** - Build Scout, Tailor, Analyzer in LangGraph; route heavy context to Gemini and rapid parsing to Groq; connect TypeScript UI to FastAPI; map JSON to core views.
* **PHASE 3 (HOURS 20-32): Automation Layer** - Wire Resend/Gmail, Remotive/Adzuna; implement Playwright browser workflow; add live WebSocket streaming for agent states.
* **PHASE 4 (HOURS 32-40): Hardening & Documentation** - End-to-end QA of Z-Axis approvals; verify YAxis -anti-fabrication guardrails; publish PRD in README; finalize live URLs and pitch assets.
* **PHASE 5 (HOURS 40-48): Pitch & Final Submission** - Dry-run demo choreography; record 5.5-minute video pitch; finalize commits; confirm cloud stability; submit repository and live URLs.

**Demo Choreography**
1. Trigger Dashboard and show live agent state transitions.
2. Review generated CV versions and ATS match outputs.
3. Open Control Tower and approve outreach through the explicit Z-Axis action.
4. Demonstrate staged application execution, emphasizing that browser actions require approval.
5. Close with the cloud architecture, governance controls, and 5.5-minute pitch narrative.

**Final Submission Checklist**
* GitHub repository contains this PRD in README.md and prominently exposes the live Azure Web App URL.
* Local setup instructions and.env.example map required secrets without committing credentials.
* Z-Axis approval gates are demonstrably enforced across CV save, email dispatch, and browser submission.
* Y-Axis guardrails block fabricated skills and synthetic professional claims.
* Final cloud build is stable, demo has been dry-run, and repository/live URLs are ready for hackathon submission.