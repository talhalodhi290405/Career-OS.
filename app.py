import streamlit as st
import requests

# 1. MUST BE THE FIRST STREAMLIT COMMAND
st.set_page_config(page_title="CareerOS - Digital FTE", page_icon="🚀", layout="wide")

# 2. LOVABLE UI CSS INJECTION
def inject_lovable_ui():
    st.markdown("""
        <style>
        .stApp {
            font-family: 'Inter', sans-serif;
        }
        .lovable-card {
            background-color: var(--background-color);
            border: 1px solid rgba(128, 128, 128, 0.2);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            transition: all 0.3s ease;
        }
        .lovable-card:hover {
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }
        .stButton>button {
            background-color: #10B981 !important;
            color: white !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            border: none !important;
            padding: 0.5rem 1rem !important;
            width: 100%;
            transition: background-color 0.2s;
        }
        .stButton>button:hover {
            background-color: #059669 !important;
        }
        .status-pending {
            border-left: 4px solid #F59E0B;
            background: rgba(245, 158, 11, 0.1);
            padding: 12px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 1rem;
        }
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }
        </style>
    """, unsafe_allow_html=True)

inject_lovable_ui()

st.title("🚀 CareerOS: Autonomous Digital FTE")
st.markdown("### Agentic Orchestration & HITL Governance")
st.markdown("---")

# 3. STRUCTURE THE UI MODULES
col1, col2 = st.columns([2, 1])

# Left Column: The Dashboard & Your API Call
with col1:
    st.markdown('<div class="lovable-card">', unsafe_allow_html=True)
    st.subheader("📊 Dynamic Dashboard")
    
    target_role = st.text_input("Enter Target Role:", "AI Engineer")
    
    if st.button("Fire Autonomous Pipeline"):
        with st.spinner("AI Agents are reading resume and sourcing matches..."):
            try:
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
                
    st.markdown('</div>', unsafe_allow_html=True)

# Right Column: The Z-Axis Governance
with col2:
    st.markdown('<div class="lovable-card">', unsafe_allow_html=True)
    st.subheader("🛡️ Control Tower (Z-Axis)")
    
    st.markdown('<div class="status-pending"><strong>Status:</strong> Execution Blocked. Awaiting Human Approval.</div>', unsafe_allow_html=True)
    
    # This acts as your Z-Axis gate for the upcoming Playwright RPA
    if st.button("Authorize Playwright RPA Execution"):
        st.success("Z-Axis Approved: Launching Headless Browser...")
        # Your JetBrains Playwright script integration will go here
        
    st.markdown('</div>', unsafe_allow_html=True)