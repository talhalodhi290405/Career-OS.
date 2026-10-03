import os
from click import prompt
import pdfplumber
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

class CareerOSState(TypedDict):
    pdf_path: str
    extracted_facts: dict       
    target_role: str
    job_matches: list
    tailored_cv: str            
    outreach_draft: str
    z_axis_approved: bool       
# LLMs are now armed

from langchain_ollama import ChatOllama
# Remove: from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

# Remove the ChatGoogleGenerativeAI line and replace with:
gemini_llm = ChatGroq(model="gemma2-9b-it")
def profile_analyzer(state: CareerOSState):
    print("--> [Agent: Profile Analyzer] Reading PDF and extracting X-Axis facts...")
    
    cv_text = ""
    try:
        with pdfplumber.open(state["pdf_path"]) as pdf:
            for page in pdf.pages:
                cv_text += page.extract_text() + "\n"
    except FileNotFoundError:
        print("    [!] ERROR: resume.pdf not found in folder!")
        return {"extracted_facts": {"error": "File not found"}}

    # Force Gemini to return clean data
    prompt = f"""
    You are an AI data extractor. Extract the candidate's top 5 technical skills and their total years of experience from this text.
    Format your response as a simple list.
    
    RESUME TEXT:
    {cv_text}
    """
    
      # response = gemini_llm.invoke(prompt)
    local_llm = ChatOllama(model="llama3") 
    response = local_llm.invoke(prompt)
    print(f"    [Success] Gemini extracted: {response.content[:100]}...") # Print a preview
        
    return {"extracted_facts": {"extracted_data": response.content}}

def job_scout(state: CareerOSState):
    print("--> [Agent: Job Scout] Sourcing live market data...")
    return {"job_matches": [{"title": state.get("target_role", "AI Engineer"), "company": "Tech Corp"}]}

def tailor(state: CareerOSState):
    print("--> [Agent: Tailor] Aligning CV (Enforcing Y-Axis Guardrails)...")
    return {"tailored_cv": "Tailored_Resume_v1.pdf"}

def hitl_governance(state: CareerOSState):
    print("--> [Governance] Staging execution for Z-Axis Human Approval...")
    return {"z_axis_approved": False} 

workflow = StateGraph(CareerOSState)

workflow.add_node("profile_analyzer", profile_analyzer)
workflow.add_node("job_scout", job_scout)
workflow.add_node("tailor", tailor)
workflow.add_node("hitl_governance", hitl_governance)

workflow.set_entry_point("profile_analyzer")
workflow.add_edge("profile_analyzer", "job_scout")
workflow.add_edge("job_scout", "tailor")
workflow.add_edge("tailor", "hitl_governance")
workflow.add_edge("hitl_governance", END)

careeros_graph = workflow.compile()