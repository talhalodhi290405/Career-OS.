import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import careeros_graph

load_dotenv()

app = FastAPI(
    title="CareerOS Engine",
    description="Autonomous Job Acquisition Digital FTE",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MissionBrief(BaseModel):
    target_role: str

@app.get("/status")
async def get_status():
    return {
        "status": "CareerOS Engine Online",
        "system": "Digital FTE Active",
        "governance": "HITL X-Y-Z Armed"
    }

@app.post("/run-engine")
async def run_engine(mission: MissionBrief):
    print(f"🚀 Initiating CareerOS Pipeline for: {mission.target_role}")
    
    initial_state = {
        "pdf_path": "resume.pdf",
        "extracted_facts": {},
        "target_role": mission.target_role,
        "job_matches": [],
        "tailored_cv": "",
        "outreach_draft": "",
        "z_axis_approved": False
    }
    
    final_state = careeros_graph.invoke(initial_state)
    
    return {
        "message": "Pipeline staged for Human Approval",
        "data": final_state
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)