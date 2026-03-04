"""OAK Hub — Problem Gallery."""
import os

import httpx
import streamlit as st

API_BASE = os.environ.get("OAK_API_URL", "http://localhost:8000")

STATUS_COLORS = {
    "pending": "🔘",
    "assembling": "🔵",
    "active": "🟢",
    "complete": "✅",
    "failed": "🔴",
}

st.set_page_config(page_title="Problem Gallery — OAK Hub", layout="wide")
st.title("Problem Gallery")

try:
    resp = httpx.get(f"{API_BASE}/api/problems", timeout=5.0)
    if resp.status_code == 200:
        problems = resp.json()
        if not problems:
            st.info("No problems submitted yet. Go to **Submit** to create one.")
        else:
            for p in problems:
                status = p.get("status", "?")
                icon = STATUS_COLORS.get(status, "⬜")
                col1, col2, col3, col4 = st.columns([0.5, 3, 1, 1.5])
                with col1:
                    st.write(icon)
                with col2:
                    st.markdown(f"**{p.get('title', 'Untitled')}**")
                    st.caption(f"`{p['id'][:8]}...` — {p.get('created_at', '?')[:16]}")
                with col3:
                    st.write(status.upper())
                with col4:
                    if st.button("View", key=f"view_{p['id']}"):
                        st.session_state["selected_problem"] = p["id"]
                        st.switch_page("pages/06_problem.py")
                    if status == "pending":
                        if st.button("Start", key=f"start_{p['id']}", type="primary"):
                            try:
                                start_resp = httpx.post(f"{API_BASE}/api/problems/{p['id']}/start", timeout=60)
                                if start_resp.status_code == 200:
                                    st.success("Pipeline started!")
                                    st.rerun()
                                else:
                                    st.error(f"Failed: {start_resp.text}")
                            except Exception as e:
                                st.error(str(e))
                st.divider()
    else:
        st.error(f"API error {resp.status_code}: {resp.text}")
except httpx.ConnectError:
    st.error("Cannot connect to OAK API. Is the stack running?")
except Exception as e:
    st.error(f"Error: {e}")
