import streamlit as st
import requests

st.set_page_config(page_title="CareerBridge AI", page_icon="🚀")

st.title("🚀 CareerBridge AI")
st.subheader("Autonomous Profile Optimization & Job Triage")

# UI Inputs
target_role = st.text_input("Enter Target Role:", "AI Engineer")

if st.button("Fire Autonomous Pipeline"):
    with st.spinner("AI Agents are reading resume and sourcing matches..."):
        try:
            # Tell the frontend to hit your FastAPI backend
            response = requests.post(
                "http://127.0.0.1:8000/run-engine", 
                json={"target_role": target_role}
            )
            
            if response.status_code == 200:
                st.success("Pipeline Executed Successfully! Staged for Human Approval.")
                st.json(response.json())
            else:
                st.error(f"Backend Error: {response.status_code}")
        except Exception as e:
            st.error("Failed to connect. Make sure your Uvicorn backend is running!")