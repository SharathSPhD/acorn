"""OAK Hub — Problem Detail page."""
import os
import time
import streamlit as st
import httpx

API_BASE = os.environ.get("OAK_API_URL", "http://localhost:8000")

st.set_page_config(page_title="Problem Detail — OAK Hub", layout="wide")

problem_id = st.query_params.get("id", st.session_state.get("selected_problem", ""))

if not problem_id:
    st.title("Problem Detail")
    st.warning("No problem selected. Go to the Gallery to pick one.")
    st.page_link("pages/03_gallery.py", label="Go to Gallery", icon="📋")
    st.stop()

try:
    resp = httpx.get(f"{API_BASE}/api/problems/{problem_id}", timeout=5.0)
    if resp.status_code != 200:
        st.error(f"Problem not found: {problem_id}")
        st.stop()
    problem = resp.json()
except httpx.ConnectError:
    st.error("Cannot connect to OAK API.")
    st.stop()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

STATUS_COLORS = {
    "pending": "gray", "assembling": "blue", "active": "green",
    "complete": "green", "failed": "red",
}
status = problem.get("status", "?")

st.title(problem.get("title", "Problem Detail"))

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Status", status.upper())
with col2:
    st.metric("ID", problem_id[:12] + "...")
with col3:
    created = problem.get("created_at", "")[:16]
    st.metric("Created", created)

if problem.get("description"):
    st.markdown(f"> {problem['description']}")

st.divider()

if status == "pending":
    if st.button("Start Pipeline", type="primary"):
        with st.spinner("Starting..."):
            try:
                start_resp = httpx.post(f"{API_BASE}/api/problems/{problem_id}/start", timeout=60)
                if start_resp.status_code == 200:
                    st.success("Pipeline started!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Failed: {start_resp.text}")
            except Exception as e:
                st.error(str(e))

tab_tasks, tab_logs, tab_files = st.tabs(["Tasks", "Logs", "Files"])

with tab_tasks:
    st.subheader("Tasks")
    try:
        tasks_resp = httpx.get(f"{API_BASE}/api/tasks?problem_id={problem_id}", timeout=5.0)
        if tasks_resp.status_code == 200:
            tasks = tasks_resp.json()
            if not tasks:
                st.info("No tasks created yet.")
            else:
                for t in tasks:
                    task_status = t.get("status", "?")
                    icon = {"pending": "⏳", "claimed": "🔄", "complete": "✅", "failed": "❌"}.get(task_status, "⬜")
                    st.markdown(f"{icon} **{t.get('title', '?')}** — `{t.get('task_type', '?')}` — {task_status}")
                    if t.get("assigned_to"):
                        st.caption(f"Assigned to: {t['assigned_to']}")
        else:
            st.warning(f"Could not load tasks: {tasks_resp.status_code}")
    except Exception as e:
        st.warning(f"Tasks not available: {e}")

with tab_logs:
    st.subheader("Container Logs")
    auto_refresh = st.checkbox("Auto-refresh (5s)", value=False, key="log_refresh")
    try:
        status_resp = httpx.get(f"{API_BASE}/api/problems/{problem_id}/status", timeout=5.0)
        if status_resp.status_code == 200:
            cs = status_resp.json()
            st.caption(f"Container: `{cs.get('container', '?')}` — {cs.get('container_status', '?')}")

        logs_resp = httpx.get(f"{API_BASE}/api/problems/{problem_id}/logs", timeout=10.0)
        if logs_resp.status_code == 200:
            logs_data = logs_resp.json()
            logs_text = logs_data.get("logs", "")
            if logs_text.strip():
                st.code(logs_text, language="text")
            else:
                st.info("No logs yet.")
        else:
            st.info("Container not started or logs unavailable.")
    except Exception as e:
        st.info(f"Logs not available: {e}")

    if auto_refresh:
        time.sleep(5)
        st.rerun()

with tab_files:
    st.subheader("Workspace Files")
    try:
        files_resp = httpx.get(f"{API_BASE}/api/problems/{problem_id}/files", timeout=5.0)
        if files_resp.status_code == 200:
            files_data = files_resp.json()
            files_list = files_data.get("files", [])
            if not files_list:
                st.info("No files in workspace yet.")
            else:
                st.caption(f"Workspace: `{files_data.get('workspace', '?')}`")
                for f in files_list:
                    size_kb = f.get("size", 0) / 1024
                    st.markdown(f"📄 **{f['name']}** — {size_kb:.1f} KB")
        else:
            st.info("Workspace not accessible.")
    except Exception as e:
        st.info(f"Files not available: {e}")

st.divider()
if problem.get("solution_url"):
    st.success(f"Solution: [{problem['solution_url']}]({problem['solution_url']})")

with st.expander("Raw problem data"):
    st.json(problem)
