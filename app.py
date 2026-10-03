import streamlit as st
import requests
import json

st.set_page_config(page_title="CareerOS - Digital FTE", page_icon="🚀", layout="wide")

st.title("🚀 CareerOS: Autonomous Digital FTE")
st.markdown("### Agentic Orchestration & HITL Governance")
st.divider()

col1, col2 = st.columns([2, 1], gap="large")

with col1:
    with st.container(border=True):
        st.subheader("📊 Dynamic Dashboard")
        target_role = st.text_input("Enter Target Role:", "AI Engineer")
        
        # UI Placeholders for dynamic updating
        terminal_log = st.empty()
        facts_box = st.empty()
        jobs_box = st.empty()
        draft_box = st.empty()
        
        if st.button("Fire Autonomous Pipeline", type="primary", use_container_width=True):
            st.session_state['pipeline_run'] = False
            terminal_log.info("🚀 Initiating LangGraph Engine...")
            
            try:
                # Use stream=True to consume Server-Sent Events
                with requests.post("http://127.0.0.1:8000/run-engine", json={"target_role": target_role}, stream=True) as response:
                    for line in response.iter_lines():
                        if line:
                            chunk = json.loads(line)
                            node = chunk.get("node")
                            status = chunk.get("status")
                            data = chunk.get("data")
                            
                            # 1. Update Live Terminal
                            terminal_log.info(f"**[{node.upper()} AGENT]** {status}")
                            
                            # 2. Render Live Data as it arrives
                            if node == "scout" and data:
                                job_html = "### 💼 Live Job Intelligence\n"
                                for j in data:
                                    job_html += f"- **{j['title']}** at {j['company']} ([View Role]({j['url']}))\n"
                                jobs_box.markdown(job_html)
                                
                            elif node == "analyzer" and data:
                                facts_box.success(f"**✅ X-Axis Facts Verified:**\n\n{data.get('extracted_data', '')}")
                                
                            elif node == "outreach" and data:
                                draft_box.markdown(f"**📧 Drafted Outreach:**\n```text\n{data}\n```")
                                
                            elif node == "system":
                                terminal_log.success("✅ LangGraph Pipeline Complete. Awaiting Human Z-Axis Approval.")
                                st.session_state['pipeline_run'] = True
                                
            except Exception as e:
                terminal_log.error(f"Backend Connection Error: {e}")

with col2:
    with st.container(border=True):
        st.subheader("🛡️ Control Tower (Z-Axis)")
        status_placeholder = st.empty()
        status_placeholder.warning("Status: Execution Blocked. Awaiting Human Approval.", icon="⚠️")
        st.markdown("<br>", unsafe_allow_html=True)
        
        pipeline_ready = st.session_state.get('pipeline_run', False)
        
        if st.button("Authorize Playwright RPA", type="primary", use_container_width=True, disabled=not pipeline_ready):
            with st.spinner("Launching Headless Browser..."):
                try:
                    rpa_response = requests.post("http://127.0.0.1:8000/execute-rpa")
                    if rpa_response.status_code == 200:
                        status_placeholder.success("Status: Execution Authorized. Application Submitted.", icon="✅")
                        st.success(rpa_response.json().get("message", "Application completed."))
                    else:
                        st.error("RPA Execution Failed.")
                except Exception:
                    st.error("Ensure Uvicorn backend is running!")