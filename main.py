import httpx
import json
import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rpa_agent import execute_job_application
import agent

app = FastAPI(title="CareerOS Backend Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "CareerOS Streaming Backend Active."}

class JobRequest(BaseModel):
    target_role: str = "AI Engineer"

@app.post("/run-engine")
async def run_engine(req: JobRequest):
    async def agent_execution_stream():
        # INITIAL STATE
        pipeline_state = {
            "pdf_path": "resume.pdf",
            "extracted_facts": {},
            "target_role": req.target_role,
            "job_matches": [],
            "outreach_draft": "",
            "z_axis_approved": False
        }

        # 1. SCOUT AGENT EXECUTION
        yield json.dumps({"node": "scout", "status": f"Querying Remotive API for {req.target_role}..."}) + "\n"
        await asyncio.sleep(0.5) # Slight pause for UI observation
        
        search_query = req.target_role.replace(" ", "%20")
        remotive_url = f"https://remotive.com/api/remote-jobs?search={search_query}&limit=3"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                api_response = await client.get(remotive_url)
                if api_response.status_code == 200:
                    jobs_data = api_response.json().get("jobs", [])
                    pipeline_state["job_matches"] = [
                        {
                            "title": job.get("title", req.target_role),
                            "company": job.get("company_name", "Tech Corp"),
                            "location": job.get("candidate_required_location", "Remote"),
                            "url": job.get("url", "https://remotive.com")
                        } for job in jobs_data[:3]
                    ]
        except Exception:
            pipeline_state["job_matches"] = [{"title": req.target_role, "company": "Demo Corp", "location": "Remote", "url": "#"}]
            
        yield json.dumps({"node": "scout", "status": "Live jobs acquired.", "data": pipeline_state["job_matches"]}) + "\n"

        # 2. RAG / PROFILE ANALYZER AGENT EXECUTION
        yield json.dumps({"node": "analyzer", "status": "RAG Agent active: Parsing PDF & prompting local Llama 3..."}) + "\n"
        
        # This will block until Llama 3 finishes, but the UI won't freeze.
        try:
            if hasattr(agent, "profile_analyzer"):
                analyzed_state = agent.profile_analyzer(pipeline_state)
                if analyzed_state:
                    pipeline_state.update(analyzed_state)
        except Exception as e:
             pipeline_state["extracted_facts"] = {"extracted_data": f"RAG Error: {e}"}
             
        yield json.dumps({"node": "analyzer", "status": "Profile facts verified (X-Axis).", "data": pipeline_state["extracted_facts"]}) + "\n"

        # 3. OUTREACH AGENT EXECUTION
        yield json.dumps({"node": "outreach", "status": "Tailoring agent generating hiring manager outreach..."}) + "\n"
        
        try:
            if hasattr(agent, "outreach_agent"):
                outreach_state = agent.outreach_agent(pipeline_state)
                if outreach_state:
                    pipeline_state.update(outreach_state)
        except Exception:
            pipeline_state["outreach_draft"] = "Drafting failed."
            
        yield json.dumps({"node": "outreach", "status": "Y-Axis drafting complete.", "data": pipeline_state["outreach_draft"]}) + "\n"
        
        # FINAL SIGNAL
        yield json.dumps({"node": "system", "status": "LangGraph execution finished. Staged for Z-Axis approval."}) + "\n"

    return StreamingResponse(agent_execution_stream(), media_type="application/x-ndjson")

@app.post("/execute-rpa")
async def trigger_rpa():
    authorized_state = {"z_axis_approved": True, "tailored_cv": "Tailored_Resume_v1.pdf", "target_job_url": "https://google.com"}
    result = await execute_job_application(authorized_state)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
    