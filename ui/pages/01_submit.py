"""OAK Hub — Submit Problem page."""
import streamlit as st
import httpx

OAK_API = st.secrets.get("OAK_API_URL", "http://localhost:8000")

st.set_page_config(page_title="OAK — Submit Problem", page_icon="🌳")
st.title("Submit a Problem")
st.markdown("Submit a new analytical problem to the OAK agent pipeline.")

with st.form("submit_problem"):
    title = st.text_input("Problem Title", placeholder="Sales Analysis Q4 2025")
    description = st.text_area(
        "Description",
        placeholder="Analyze Q4 sales data to identify top regions and products...",
        height=120,
    )
    tags_raw = st.text_input("Tags (comma-separated)", placeholder="csv, analysis, regression")
    submitted = st.form_submit_button("Submit Problem")

if submitted:
    if not title or not description:
        st.error("Title and description are required.")
    else:
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        try:
            resp = httpx.post(
                f"{OAK_API}/api/problems",
                json={"title": title, "description": description, "tags": tags},
                timeout=10,
            )
            resp.raise_for_status()
            problem = resp.json()
            uuid = problem["id"]
            st.success(f"✅ Problem created: `{uuid}`")
            st.code(f"bash scripts/new-problem.sh {uuid}", language="bash")
            st.info("Run the command above on the DGX node to start the agent pipeline.")
            st.json(problem)
        except Exception as e:
            st.error(f"Failed to submit: {e}")

st.divider()
st.subheader("Model Routing")
try:
    models = httpx.get(f"{OAK_API}/api/agents/models", timeout=5).json()
    st.json(models)
except Exception:
    st.warning("API not reachable — start the OAK stack first.")
