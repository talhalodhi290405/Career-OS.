import pdfplumber
import time
from langchain_ollama import ChatOllama
from typing import TypedDict

# --- Configuration ---
HACKATHON_DEMO_MODE = True  # Set to False to use live local Llama 3

# Define the unified graph state
class CareerOSState(TypedDict):
    pdf_path: str
    extracted_facts: dict
    target_role: str
    job_matches: list
    tailored_cv: str
    outreach_draft: str
    z_axis_approved: bool

# Initialize local Llama 3 (No API keys needed)
local_llm = None
if not HACKATHON_DEMO_MODE:
    try:
        local_llm = ChatOllama(model="llama3")
    except Exception as e:
        print(f"--> [Warning] Could not initialize Llama 3: {e}")


def profile_analyzer(state: dict) -> dict:
    """
    X-Axis Agent: Extracts structured facts from a candidate's PDF resume
    using pdfplumber + local Llama 3 (or a demo stub in HACKATHON_DEMO_MODE).
    """
    print("--> [Agent: Profile Analyzer] Reading PDF and extracting X-Axis facts...")

    if HACKATHON_DEMO_MODE:
        time.sleep(1.5)  # Simulate processing time for live demo
        demo_facts = (
            "Top Skills: Python, LangGraph, FastAPI, Playwright, Streamlit\n"
            "Experience: 3+ years building agentic AI systems and RPA pipelines."
        )
        print("--> [Agent: Profile Analyzer] Demo extraction successful.")
        return {"extracted_facts": {"extracted_data": demo_facts}}

    # Live pdfplumber + Llama 3 logic
    cv_text = ""
    pdf_path = state.get("pdf_path", "resume.pdf")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    cv_text += extracted + "\n"

        prompt = (
            f"Extract the top 5 technical skills and total years of experience "
            f"from this candidate's resume:\n\n{cv_text}"
        )
        response = local_llm.invoke(prompt)
        print("--> [Agent: Profile Analyzer] Extraction successful.")
        return {"extracted_facts": {"extracted_data": response.content}}

    except Exception as e:
        print(f"--> [Error] Profile Analyzer failed: {e}")
        return {"extracted_facts": {"extracted_data": f"Failed to parse PDF or connect to Llama 3: {e}"}}


def outreach_agent(state: dict) -> dict:
    """
    Y-Axis Agent: Drafts a personalized, role-specific outreach email using
    local Llama 3 (or a demo stub in HACKATHON_DEMO_MODE).
    """
    print("--> [Agent: Outreach] Drafting personalized outreach...")

    target_role = state.get("target_role", "AI Engineer")
    top_job = state.get("job_matches", [{}])[0].get("company", "Tech Corp")

    if HACKATHON_DEMO_MODE:
        time.sleep(1.0)
        draft = (
            f"Subject: Application for {target_role} at {top_job}\n\n"
            f"Hi Hiring Team,\n\n"
            f"I am writing to express my interest in the {target_role} position. "
            f"With a strong foundation in building autonomous digital FTEs, Python, and LangGraph orchestration, "
            f"I am well-equipped to drive immediate impact at {top_job}.\n\n"
            f"My complete application is attached. I look forward to discussing how "
            f"my background aligns with your goals.\n\n"
            f"Best regards,\nTalha Lodhi"
        )
        print("--> [Agent: Outreach] Demo draft successful.")
        return {"outreach_draft": draft}

    # Live Llama 3 logic
    if local_llm:
        prompt = f"Draft a concise, professional cold email for a {target_role} position at {top_job}."
        try:
            response = local_llm.invoke(prompt)
            return {"outreach_draft": response.content}
        except Exception as e:
            return {"outreach_draft": f"Failed to generate draft: {e}"}

    return {"outreach_draft": "LLM not initialized."}