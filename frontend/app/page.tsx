"use client";

import {
  Activity,
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  BarChart3,
  BriefcaseBusiness,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  FileBadge,
  FileText,
  FolderKanban,
  LayoutDashboard,
  LoaderCircle,
  LockKeyhole,
  Mail,
  MapPin,
  MessageSquareText,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Play,
  Radio,
  Search,
  ShieldCheck,
  Sparkles,
  Sun,
  Upload,
  Users,
  type LucideIcon,
} from "lucide-react";
import { ChangeEvent, FormEvent, useEffect, useState } from "react";

const API_URL = "/api/backend";

type PageKey = "dashboard" | "cv" | "jobs" | "outreach" | "interview" | "control";
type Job = {
  title: string;
  company: string;
  location?: string;
  description?: string;
  url: string;
  source?: string;
  skills?: string[];
  matched_profile_skills?: string[];
  profile_match_pct?: number;
};
type AgentMetric = { status?: string; total_tokens?: number; latency_seconds?: number };
type CareerState = {
  profile_data: Record<string, unknown>;
  job_listings: Job[];
  tailored_cv: string;
  tailored_cv_path: string;
  cover_letter: string;
  outreach_draft: string;
  interview_prep: string[];
  agent_metrics: Record<string, AgentMetric>;
  api_metrics: Record<string, Record<string, unknown>>;
  ats_score: number;
};
type EventRow = { agent: string; message: string; kind: string };
type Theme = "dark" | "light";

const pages: { id: PageKey; label: string; icon: LucideIcon; group: string }[] = [
  { id: "dashboard", label: "Dynamic Dashboard", icon: LayoutDashboard, group: "WORKSPACE" },
  { id: "cv", label: "CV Versions Hub", icon: FileBadge, group: "WORKSPACE" },
  { id: "jobs", label: "Job Intelligence", icon: BriefcaseBusiness, group: "WORKSPACE" },
  { id: "outreach", label: "Outreach", icon: Mail, group: "COMMUNICATION" },
  { id: "interview", label: "Interview Prep", icon: MessageSquareText, group: "COMMUNICATION" },
  { id: "control", label: "Control Tower", icon: ShieldCheck, group: "GOVERNANCE" },
];

const initialData: CareerState = {
  profile_data: {},
  job_listings: [],
  tailored_cv: "",
  tailored_cv_path: "",
  cover_letter: "",
  outreach_draft: "",
  interview_prep: [],
  agent_metrics: {},
  api_metrics: {},
  ats_score: 0,
};

function parseFrame(frame: string): { event: string; payload: Record<string, unknown> } | null {
  let event = "message";
  const data: string[] = [];
  for (const line of frame.split(/\r?\n/)) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
  }
  if (!data.length) return null;
  try {
    return { event, payload: JSON.parse(data.join("\n")) as Record<string, unknown> };
  } catch {
    return { event: "error", payload: { status: "Invalid event data from backend." } };
  }
}

export default function Home() {
  const [page, setPage] = useState<PageKey>("dashboard");
  const [theme, setTheme] = useState<Theme>("dark");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [targetRole, setTargetRole] = useState("AI Engineer");
  const [targetLocation, setTargetLocation] = useState("");
  const [workplaceType, setWorkplaceType] = useState("Any");
  const [atsStrictness, setAtsStrictness] = useState(65);
  const [resume, setResume] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState<CareerState>(initialData);
  const [events, setEvents] = useState<EventRow[]>([]);
  const [tokens, setTokens] = useState<Record<string, string>>({});
  const [threadId, setThreadId] = useState("");
  const [pipelineReady, setPipelineReady] = useState(false);
  const [approved, setApproved] = useState(false);
  const [rpaResult, setRpaResult] = useState<Record<string, string> | null>(null);
  const [credentials, setCredentials] = useState({
    groq: "",
    gemini: "",
    pinecone: "",
    pineconeIndex: "",
    adzunaId: "",
    adzunaKey: "",
    jsearch: "",
  });

  useEffect(() => {
    const saved = window.localStorage.getItem("careeros-theme");
    if (saved === "light" || saved === "dark") setTheme(saved);
  }, []);

  const requestHeaders = () => ({
    ...(credentials.groq && { "X-Groq-Api-Key": credentials.groq }),
    ...(credentials.gemini && { "X-Google-Api-Key": credentials.gemini }),
    ...(credentials.pinecone && { "X-Pinecone-Api-Key": credentials.pinecone }),
    ...(credentials.pineconeIndex && { "X-Pinecone-Index-Name": credentials.pineconeIndex }),
    ...(credentials.adzunaId && { "X-Adzuna-App-Id": credentials.adzunaId }),
    ...(credentials.adzunaKey && { "X-Adzuna-App-Key": credentials.adzunaKey }),
    ...(credentials.jsearch && { "X-JSearch-Api-Key": credentials.jsearch }),
  });

  const consumeSse = async (
    response: Response,
    onEvent: (event: string, payload: Record<string, unknown>) => void,
  ) => {
    if (!response.body) throw new Error("Streaming response body is unavailable.");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let pending = "";
    while (true) {
      const { value, done } = await reader.read();
      pending += decoder.decode(value, { stream: !done });
      const frames = pending.split(/\r?\n\r?\n/);
      pending = frames.pop() || "";
      for (const frame of frames) {
        const parsed = parseFrame(frame);
        if (parsed) onEvent(parsed.event, parsed.payload);
      }
      if (done) break;
    }
    if (pending.trim()) {
      const parsed = parseFrame(pending);
      if (parsed) onEvent(parsed.event, parsed.payload);
    }
  };

  const handleEvent = (event: string, payload: Record<string, unknown>) => {
    if (event === "started") setThreadId(String(payload.thread_id || ""));
    if (event === "status") {
      setEvents((current) => [...current, {
        agent: String(payload.agent || "Agent"),
        message: String(payload.message || ""),
        kind: "status",
      }]);
    }
    if (event === "token") {
      const agent = String(payload.agent || "agent");
      const token = String(payload.token || "");
      setTokens((current) => ({ ...current, [agent]: (current[agent] || "") + token }));
    }
    if (event === "token_reset") {
      const agent = String(payload.agent || "agent");
      setTokens((current) => ({ ...current, [agent]: "" }));
    }
    if (event === "node") {
      const patch = payload.data as Partial<CareerState> | undefined;
      if (patch) setData((current) => ({
        ...current,
        ...patch,
        agent_metrics: { ...current.agent_metrics, ...(patch.agent_metrics || {}) },
        api_metrics: { ...current.api_metrics, ...(patch.api_metrics || {}) },
      }));
      setEvents((current) => [...current, {
        agent: String(payload.node || "Agent"),
        message: String(payload.status || "Completed"),
        kind: "node",
      }]);
    }
    if (event === "interrupt") {
      const patch = payload.data as Partial<CareerState> | undefined;
      if (patch) setData((current) => ({ ...current, ...patch }));
      setPipelineReady(Boolean(payload.artifact_ready));
      setApproved(false);
      setEvents((current) => [...current, {
        agent: "Z-Axis",
        message: String(payload.status || "Waiting for approval"),
        kind: "interrupt",
      }]);
    }
    if (event === "approved") setApproved(Boolean(payload.z_axis_approved ?? true));
    if (event === "rpa_result") setRpaResult(payload as Record<string, string>);
    if (event === "error") setError(String(payload.status || "Pipeline failed."));
  };

  const resetRun = () => {
    setData(initialData);
    setEvents([]);
    setTokens({});
    setThreadId("");
    setPipelineReady(false);
    setApproved(false);
    setRpaResult(null);
    setError("");
  };

  const runPipeline = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!resume) {
      setError("Upload a resume PDF to start the pipeline.");
      return;
    }
    resetRun();
    setBusy(true);
    try {
      const form = new FormData();
      form.append("target_role", targetRole.trim());
      form.append("target_location", targetLocation.trim());
      form.append("workplace_type", workplaceType);
      form.append("ats_strictness", String(atsStrictness));
      form.append("file", resume);
      const response = await fetch(`${API_URL}/run-pipeline`, {
        method: "POST",
        headers: requestHeaders(),
        body: form,
      });
      if (!response.ok) throw new Error((await response.text()) || `Request failed: ${response.status}`);
      await consumeSse(response, handleEvent);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Pipeline request failed.");
    } finally {
      setBusy(false);
    }
  };

  const authorizeRpa = async () => {
    if (!threadId) {
      setError("No active pipeline run is ready for authorization.");
      return;
    }
    setBusy(true);
    try {
      const response = await fetch(`${API_URL}/approve-z-axis`, {
        method: "POST",
        headers: { ...requestHeaders(), "X-CareerOS-Thread-ID": threadId },
      });
      if (!response.ok) throw new Error((await response.text()) || `Approval failed: ${response.status}`);
      await consumeSse(response, handleEvent);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Approval request failed.");
    } finally {
      setBusy(false);
    }
  };

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    window.localStorage.setItem("careeros-theme", next);
  };

  const downloadText = (filename: string, text: string) => {
    const url = URL.createObjectURL(new Blob([text], { type: "text/markdown;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  const totalTokens = Object.values(data.agent_metrics).reduce(
    (sum, metric) => sum + Number(metric.total_tokens || 0), 0,
  );
  const apiQuota = `A: ${data.api_metrics.adzuna?.remaining ?? "--"} · J: ${data.api_metrics.jsearch?.remaining ?? "--"}`;
  const profile = data.profile_data;
  const activePage = pages.find((item) => item.id === page);

  const pageHeader = (eyebrow: string, title: string, description: string) => (
    <div className="page-head">
      <div>
        <div className="page-eyebrow">{eyebrow}</div>
        <h1 className="page-title">{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      <div className="run-chip"><span className={`status-dot ${pipelineReady ? "ready" : approved ? "approved" : ""}`} />{pipelineReady ? "REVIEW READY" : approved ? "AUTHORIZED" : "SYSTEM READY"}</div>
    </div>
  );

  const metrics = (
    <div className="metric-grid">
      <Metric label="JOB API QUOTA" value={apiQuota} foot="Adzuna · JSearch" icon={Radio} />
      <Metric label="ATS ALIGNMENT" value={data.ats_score ? `${data.ats_score}%` : "—"} foot="Verified-skill overlap" icon={BarChart3} />
      <Metric label="AGENT TOKENS" value={totalTokens.toLocaleString()} foot="Across active run" icon={Activity} />
    </div>
  );

  return (
    <div className="app-shell" data-theme={theme}>
      <aside className={`sidebar ${sidebarOpen ? "" : "collapsed"}`} aria-label="CareerOS navigation">
        <div className="brand">
          <div className="brand-mark"><Sparkles size={17} /></div>
          <div className="brand-copy"><div className="brand-name">CareerOS</div><div className="brand-sub">DIGITAL FTE / CONTROL PLANE</div></div>
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav className="nav-list" aria-label="Main navigation">
          {pages.map(({ id, label, icon: Icon, group }, index) => {
            const previous = pages[index - 1];
            return (
              <div key={id}>
                {(!previous || previous.group !== group) && <div className="nav-label group-label">{group}</div>}
                <button className={`nav-item ${page === id ? "active" : ""}`} onClick={() => setPage(id)} title={label} aria-current={page === id ? "page" : undefined}>
                  <Icon size={17} strokeWidth={1.8} /><span>{label}</span>
                </button>
              </div>
            );
          })}
        </nav>
        <div className="sidebar-spacer" />
        <section className="governance-card">
          <div className="governance-head"><ShieldCheck size={14} /> HUMAN-IN-THE-LOOP</div>
          <div className="governance-status"><span className={`status-dot ${approved ? "approved" : pipelineReady ? "ready" : ""}`} />
            {approved ? "Approval recorded" : pipelineReady ? "Review required" : "Execution locked"}
          </div>
          <button className="approve-button" disabled={!pipelineReady || approved || busy} onClick={authorizeRpa}>
            {busy ? <LoaderCircle size={14} className="spin" /> : <LockKeyhole size={14} />} Authorize browser prep
          </button>
        </section>
        <details className="credential-details">
          <summary><FolderKanban size={14} /> System credentials</summary>
          <div className="credential-fields">
            <Credential label="Groq API key" value={credentials.groq} onChange={(value) => setCredentials({ ...credentials, groq: value })} />
            <Credential label="Gemini API key" value={credentials.gemini} onChange={(value) => setCredentials({ ...credentials, gemini: value })} />
            <Credential label="Pinecone API key" value={credentials.pinecone} onChange={(value) => setCredentials({ ...credentials, pinecone: value })} />
            <label>Pinecone index<input value={credentials.pineconeIndex} onChange={(event) => setCredentials({ ...credentials, pineconeIndex: event.target.value })} autoComplete="off" /></label>
            <Credential label="Adzuna app ID" value={credentials.adzunaId} onChange={(value) => setCredentials({ ...credentials, adzunaId: value })} />
            <Credential label="Adzuna app key" value={credentials.adzunaKey} onChange={(value) => setCredentials({ ...credentials, adzunaKey: value })} />
            <Credential label="JSearch API key" value={credentials.jsearch} onChange={(value) => setCredentials({ ...credentials, jsearch: value })} />
          </div>
        </details>
        <div className="sidebar-foot"><span className="live-indicator" /> LOCAL CONTROL PLANE</div>
      </aside>

      <div className={`main-shell ${sidebarOpen ? "" : "expanded"}`}>
        <header className="topbar">
          <div className="topbar-left">
            <span className="topbar-context">CAREEROS <span className="breadcrumb">/</span> {activePage?.label.toUpperCase()}</span>
          </div>
          <div className="topbar-actions">
            <span className="top-status"><span className="live-indicator" /> AGENTS ONLINE</span>
            <button className="icon-button" onClick={() => setSidebarOpen((open) => !open)} aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"} title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}>
              {sidebarOpen ? <PanelLeftClose size={17} /> : <PanelLeftOpen size={17} />}
            </button>
            <button className="theme-toggle" onClick={toggleTheme} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>
              {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}<span>{theme === "dark" ? "Light" : "Dark"}</span>
            </button>
          </div>
        </header>

        <main className="main-content">
          {page === "dashboard" && (
            <>
              {pageHeader("X · Y · Z GOVERNANCE / OVERVIEW", "Your career, in motion.", "From verified candidate facts to live roles, tailored materials, and human-reviewed browser preparation.")}
              {metrics}
              <section className="surface">
                <div className="surface-head"><div><h2 className="surface-title">Launch a pipeline</h2><div className="surface-note">Profile facts stay grounded in the uploaded resume.</div></div><div className="run-chip"><Radio size={12} /> LIVE SOURCES</div></div>
                <form onSubmit={runPipeline}>
                  <div className="pipeline-form">
                    <Field label="Target role"><input value={targetRole} onChange={(event) => setTargetRole(event.target.value)} placeholder="e.g. Applied AI Engineer" required /></Field>
                    <Field label="Location"><input value={targetLocation} onChange={(event) => setTargetLocation(event.target.value)} placeholder="Any city, region, or country" /></Field>
                    <Field label="Work mode"><select value={workplaceType} onChange={(event) => setWorkplaceType(event.target.value)}><option>Any</option><option>Remote</option><option>Hybrid</option><option>On-site</option></select></Field>
                    <Field label="Resume PDF"><input type="file" accept="application/pdf,.pdf" onChange={(event: ChangeEvent<HTMLInputElement>) => setResume(event.target.files?.[0] || null)} required /></Field>
                  </div>
                  <div className="form-bottom">
                    <button className="primary-button" type="submit" disabled={busy || !resume}>{busy ? <LoaderCircle size={15} className="spin" /> : <Play size={14} fill="currentColor" />} {busy ? "Agents working" : "Start career pipeline"}</button>
                    <span className="surface-note"><MapPin size={12} /> {workplaceType} · {targetLocation || "Any location"}</span>
                  </div>
                </form>
              </section>
              {error && <div className="error-banner"><CircleAlert size={15} /> {error}</div>}
              {pipelineReady && <div className="success-banner"><Check size={15} /> Materials staged. Review them before authorizing browser preparation.</div>}
              <div className="dashboard-grid">
                <section className="surface">
                  <div className="surface-head"><h2 className="surface-title">Agent activity</h2><span className="surface-note">REAL-TIME EVENT STREAM</span></div>
                  {events.length ? <div className="timeline">{events.slice(-12).map((entry, index) => <div className="timeline-row" key={`${entry.agent}-${index}`}><span className="timeline-mark" /><div className="timeline-copy"><strong>{entry.agent.replaceAll("_", " ")}</strong> · {entry.message}</div></div>)}</div> : <div className="empty-state"><div><Activity size={22} /><strong>Waiting for a new run</strong>Agent status and provider updates appear here as the graph executes.</div></div>}
                  {Object.entries(tokens).map(([agent, text]) => text && <div className="token-stream" key={agent}><strong>{agent.replaceAll("_", " ").toUpperCase()}</strong>{"\n"}{text.slice(-2500)}</div>)}
                </section>
                <section className="surface">
                  <div className="surface-head"><h2 className="surface-title">X-axis · candidate truth</h2><span className="surface-note">SOURCE-VERIFIED</span></div>
                  {Object.keys(profile).length ? <><div className="profile-fact"><strong>{String(profile.name || "Candidate")}</strong><br />{String(profile.headline || "Verified profile")}{profile.experience_years ? ` · ${profile.experience_years} years` : ""}<p>{String(profile.summary || "")}</p></div><div className="skill-list">{((profile.skills as string[]) || []).map((skill) => <span className="skill-tag" key={skill}>{skill}</span>)}</div></> : <div className="empty-state"><div><Users size={22} /><strong>No verified profile yet</strong>Upload a resume to extract and cross-check the candidate facts.</div></div>}
                </section>
              </div>
            </>
          )}

          {page === "cv" && <>
            {pageHeader("DOCUMENTS / TAILORING", "CV & cover letter", "Two role-specific documents, grounded in the source resume and retrieved profile facts.")}
            <div className="profile-layout">
              <DocumentPanel title="Tailored CV" icon={FileText} content={data.tailored_cv} onDownload={() => downloadText("careeros-tailored-cv.md", data.tailored_cv)} />
              <DocumentPanel title="Cover letter" icon={FileBadge} content={data.cover_letter} onDownload={() => downloadText("careeros-cover-letter.md", data.cover_letter)} />
            </div>
            {data.tailored_cv_path && <DownloadPdf path={data.tailored_cv_path} />}
            {!data.tailored_cv && <Empty title="No generated documents" text="Run the pipeline to generate a tailored CV and cover letter." icon={FileText} />}
          </>}

          {page === "jobs" && <>
            {pageHeader("MARKET / OPPORTUNITIES", "Job intelligence", "Live Adzuna and JSearch roles filtered by your target role, location, and work mode.")}
            {metrics}
            {data.job_listings.length ? <JobTable jobs={data.job_listings} /> : <Empty title="No live listings yet" text="Start a pipeline to source and compare current roles." icon={Search} />}
          </>}

          {page === "outreach" && <>
            {pageHeader("COMMUNICATION / OUTREACH", "Make the first move.", "A recruiter-ready email grounded in verified candidate facts and the selected live role.")}
            {data.outreach_draft ? <DocumentPanel title="Hiring manager email" icon={Mail} content={data.outreach_draft} onDownload={() => downloadText("careeros-outreach.md", data.outreach_draft)} /> : <Empty title="No draft yet" text="Run the pipeline to generate contextual outreach." icon={Mail} />}
          </>}

          {page === "interview" && <>
            {pageHeader("PRACTICE / PREPARATION", "Walk in ready.", "Role-specific behavioral prompts designed around Situation, Task, Action, and Result.")}
            {data.interview_prep.length ? <div className="question-list">{data.interview_prep.map((question, index) => <div className="question-card" key={`${index}-${question}`}><span className="question-number">STAR / {String(index + 1).padStart(2, "0")}</span><span className="question-text">{question}</span></div>)}</div> : <Empty title="Interview prep is empty" text="The prep agent will create role-specific questions after the live role match." icon={MessageSquareText} />}
          </>}

          {page === "control" && <>
            {pageHeader("GOVERNANCE / HUMAN IN THE LOOP", "Control tower", "The browser can prepare an application, but it will stop before submission for human review.")}
            <div className="control-grid">
              <section className="surface"><div className="surface-head"><h2 className="surface-title">Z-axis authorization</h2><ShieldCheck size={18} color="var(--accent)" /></div><div className={approved ? "success-banner" : pipelineReady ? "notice-banner" : "empty-state"}>{approved ? "Approval recorded. Browser preparation is authorized." : pipelineReady ? "Review the candidate profile, live job, and generated materials before approving." : "No pipeline is staged for approval."}</div><button className="primary-button" disabled={!pipelineReady || approved || busy} onClick={authorizeRpa}>{busy ? <LoaderCircle size={15} className="spin" /> : <LockKeyhole size={15} />} Authorize browser preparation</button>{rpaResult && <p className="surface-note">{rpaResult.message}</p>}</section>
              <section className="surface"><div className="surface-head"><h2 className="surface-title">Agent trace</h2><span className="surface-note">LANGGRAPH RUN</span></div>{events.length ? <div className="timeline">{events.slice(-20).map((entry, index) => <div className="timeline-row" key={`${entry.agent}-${index}`}><span className="timeline-mark" /><div className="timeline-copy"><strong>{entry.agent.replaceAll("_", " ")}</strong> · {entry.message}</div></div>)}</div> : <div className="surface-note">Run events will appear here.</div>}</section>
            </div>
            <section className="surface" style={{ marginTop: 14 }}><div className="surface-head"><h2 className="surface-title">Agent health</h2><span className="surface-note">TOKEN USAGE · LATENCY · STATUS</span></div><div className="agent-grid">{Object.entries(data.agent_metrics).map(([name, metric]) => <div className="agent-row" key={name}><strong>{name.replaceAll("_", " ")}</strong><span>{metric.status || `${metric.total_tokens || 0} tokens · ${metric.latency_seconds || 0}s`}</span></div>)}</div></section>
          </>}
        </main>
      </div>
    </div>
  );
}

function Metric({ label, value, foot, icon: Icon }: { label: string; value: string; foot: string; icon: LucideIcon }) {
  return <div className="metric-card"><div className="metric-label"><Icon size={13} /> {label}</div><div className="metric-value">{value}</div><div className="metric-foot">{foot}</div></div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="field"><span>{label}</span>{children}</label>;
}

function Credential({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label>{label}<input type="password" value={value} onChange={(event) => onChange(event.target.value)} autoComplete="new-password" spellCheck={false} /></label>;
}

function Empty({ title, text, icon: Icon }: { title: string; text: string; icon: LucideIcon }) {
  return <div className="empty-state"><div><Icon size={22} /><strong>{title}</strong>{text}</div></div>;
}

function DocumentPanel({ title, icon: Icon, content, onDownload }: { title: string; icon: LucideIcon; content: string; onDownload: () => void }) {
  return <section className="surface"><div className="surface-head"><h2 className="surface-title"><Icon size={15} /> {title}</h2>{content && <button className="icon-button" onClick={onDownload} title={`Download ${title}`}><ArrowDownToLine size={15} /></button>}</div>{content ? <div className="markdown-output">{content.split("\n").map((line, index) => <p key={`${index}-${line}`}>{line || " "}</p>)}</div> : <Empty title={`${title} not generated`} text="Complete the dashboard run to create this document." icon={Icon} />}</section>;
}

function DownloadPdf({ path }: { path: string }) {
  return <p className="surface-note" style={{ marginTop: 12 }}><FileText size={13} /> A PDF artifact is staged server-side for the approved browser session.</p>;
}

function JobTable({ jobs }: { jobs: Job[] }) {
  return <div className="table-wrap"><table className="jobs-table"><thead><tr><th>ROLE</th><th>LOCATION</th><th>FIT</th><th>SOURCE</th><th>RESUME SKILLS</th><th>LINK</th></tr></thead><tbody>{jobs.map((job, index) => <tr key={`${job.url}-${index}`}><td><div className="job-title">{job.title}</div><div className="job-sub">{job.company}</div></td><td>{job.location || "Not specified"}</td><td><strong>{job.profile_match_pct ?? 0}%</strong></td><td><span className="mini-tag">{job.source || "Live"}</span></td><td><div className="tag-row">{(job.matched_profile_skills || []).slice(0, 5).map((skill) => <span className="mini-tag" key={skill}>{skill}</span>)}</div></td><td><a href={job.url} target="_blank" rel="noreferrer">View role <ArrowRight size={12} /></a></td></tr>)}</tbody></table></div>;
}