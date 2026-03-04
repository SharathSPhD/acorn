"""OAK Hub — Submit Problem page."""
import os
import streamlit as st
import httpx

API_BASE = os.environ.get("OAK_API_URL", "http://localhost:8000")

st.set_page_config(page_title="OAK — Submit Problem", page_icon="🌳", layout="wide")
st.title("Submit a Problem")
st.markdown("Submit a new analytical problem. The agent pipeline starts automatically.")

with st.form("submit_problem"):
    title = st.text_input("Problem Title", placeholder="Sales Analysis Q4 2025")
    description = st.text_area(
        "Description",
        placeholder="Analyze Q4 sales data to identify top regions and products...",
        height=120,
    )
    uploaded_file = st.file_uploader(
        "Upload data file (optional)",
        type=["csv", "json", "xlsx", "parquet"],
        help="Upload a dataset for the agents to work with",
    )
    auto_start = st.checkbox("Start pipeline automatically", value=True)
    submitted = st.form_submit_button("Submit Problem", type="primary")

if submitted:
    if not title or not description:
        st.error("Title and description are required.")
    else:
        try:
            resp = httpx.post(
                f"{API_BASE}/api/problems",
                json={"title": title, "description": description},
                timeout=10,
            )
            resp.raise_for_status()
            problem = resp.json()
            uuid = problem["id"]
            st.success(f"Problem created: `{uuid}`")

            if uploaded_file is not None:
                with st.spinner("Uploading file..."):
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "application/octet-stream")}
                    upload_resp = httpx.post(
                        f"{API_BASE}/api/problems/{uuid}/upload",
                        files=files,
                        timeout=30,
                    )
                    if upload_resp.status_code == 200:
                        st.info(f"File uploaded: {uploaded_file.name}")
                    else:
                        st.warning(f"File upload failed: {upload_resp.text}")

            if auto_start:
                with st.spinner("Starting agent pipeline..."):
                    start_resp = httpx.post(
                        f"{API_BASE}/api/problems/{uuid}/start",
                        timeout=60,
                    )
                    if start_resp.status_code == 200:
                        start_data = start_resp.json()
                        st.success(f"Pipeline started: {start_data.get('container_name', '?')}")
                        st.page_link("pages/06_problem.py", label=f"View Problem {uuid[:8]}...", icon="📊")
                    else:
                        st.error(f"Pipeline start failed: {start_resp.text}")
                        st.code(f"bash scripts/new-problem.sh {uuid}", language="bash")
            else:
                st.info("Pipeline not started. Start it manually or from the Gallery.")

        except httpx.ConnectError:
            st.error("Cannot connect to OAK API. Is the stack running?")
        except Exception as e:
            st.error(f"Failed to submit: {e}")
