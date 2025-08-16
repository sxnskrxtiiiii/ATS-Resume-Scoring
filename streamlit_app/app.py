import streamlit as st
import requests
import pandas as pd
import time
import re
import json
from components import show_score_chart, show_suggestions, show_job_recommendations

# === Backend URL ===
BACKEND_URL = "http://localhost:5000"  # change if backend URL is different

# === Page Config ===
st.set_page_config(page_title="ATS System", page_icon="📄", layout="wide")

# === Custom CSS ===
try:
    st.markdown("<style>" + open("streamlit_app/styles.css").read() + "</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("⚠ styles.css not found — using default Streamlit style.")

# === Session Defaults ===
if "auth" not in st.session_state:
    st.session_state.auth = {"is_authenticated": False, "email": None, "name": None}
if "active_page" not in st.session_state:
    st.session_state.active_page = "🏠 Home / Dashboard"

pages = [
    "🏠 Dashboard",
    "📄 Upload Job Description",
    "📑 Upload Resume & Get Score",
    "🛠  Improvement Suggestions",
    "💼 Job Recommendations",
    "📊 Reports",
]

# === Auth Handlers ===
def set_auth(email, name):
    st.session_state.auth = {"is_authenticated": True, "email": email, "name": name}

def sign_out():
    st.session_state.auth = {"is_authenticated": False, "email": None, "name": None}
    st.session_state.active_page = "🏠 Home / Dashboard"
    st.rerun()

# === Top Navigation (Streamlit-native buttons, instant switching) ===
def render_topnav():
    if not st.session_state.auth["is_authenticated"]:
        return

    cols = st.columns(len(pages) + 1)
    for i, p in enumerate(pages):
        icon = p.split(" ", 1)[0]
        label = p.split(" ", 1)[1]
        if cols[i].button(f"{icon} {label}", key=f"nav_{i}"):
            st.session_state.active_page = p
            st.rerun()

    if cols[-1].button("→ Sign out", key="nav_signout"):
        sign_out()

    st.markdown("<hr>", unsafe_allow_html=True)

# === Login Screen ===
def render_login():
    left, right = st.columns([1.1, 0.9], gap="large")

    with left:
        st.markdown('<div class="card glass">', unsafe_allow_html=True)
        st.markdown("""
            <div class="hero" style="margin:0;">
                <div class="hero-content">
                    <div class="hero-title">Welcome to ATS Score</div>
                    <div class="hero-subtitle">Sign in to analyze your resume, match JDs, and get instant insights.</div>
                </div>
            </div>
            <div style="margin-top:10px;color:#cbd5e1;">
                <p>• Instant scoring and recruiter‑style feedback</p>
                <p>• JD matching with missing skills highlights</p>
                <p>• Exportable reports and charts</p>
            </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Log in to your account</div>', unsafe_allow_html=True)

        mode = st.segmented_control("Mode", options=["Login", "Sign up"], default="Login")
        email = st.text_input("E-mail", placeholder="name@email.com")
        password = st.text_input("Password", type="password", placeholder="6–50 chars, include letters and numbers")
        name = None
        if mode == "Sign up":
            name = st.text_input("Name", placeholder="Your name")

        if st.button("Continue", use_container_width=True):
            valid_email = re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", (email or "").strip()) is not None
            valid_pwd = 6 <= len(password or "") <= 50 and re.search(r"[A-Za-z]", password or "") and re.search(r"\d", password or "")
            if not valid_email:
                st.error("Invalid email address.")
            elif not valid_pwd:
                st.error("Password must be 6–50 chars, with letters and numbers.")
            elif mode == "Sign up" and not (name or "").strip():
                st.error("Please enter your name.")
            else:
                display_name = (name or "").strip() or email.split("@")[0]
                set_auth(email.strip(), display_name)
                st.rerun()

        st.markdown("""
            <div style="margin-top:10px;color:#94a3b8;font-size:13px;">
                Or continue with:
            </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🟦  Continue with Google", use_container_width=True):
                st.toast("Google sign-in not implemented yet.", icon="ℹ️")
        with c2:
            if st.button("🔷  Continue with Facebook", use_container_width=True):
                st.toast("Facebook sign-in not implemented yet.", icon="ℹ️")

        st.markdown('</div>', unsafe_allow_html=True)

# === Auth Gate ===
if not st.session_state.auth["is_authenticated"]:
    render_login()
    st.stop()

# === Show top nav after login ===
render_topnav()

# === PAGE 0 — Dashboard ===
if st.session_state.active_page == pages[0]:
    st.markdown("""
        <div class="hero">
            <div class="hero-content">
                <div class="hero-title">ATS Command Center</div>
                <div class="hero-subtitle">Track history, manage resumes & JDs, and view analytics in one place.</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="card glass">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Recent History</div>', unsafe_allow_html=True)
    try:
        # Fetch history with a cache-buster
        resp = requests.get(
            f"{BACKEND_URL}/history",
            params={"limit": 20, "offset": 0, "_": int(time.time())},
            timeout=10
        )
        if not resp.ok:
            st.error(f"History fetch failed: {resp.status_code} {resp.text}")
        else:
            payload = resp.json()  # {"items":[...], "total":N, "limit":..., "offset":...}
            rows = payload.get("items", [])
            df = pd.DataFrame(rows)

            if "selected_resume_hash" not in st.session_state:
                st.session_state.selected_resume_hash = ""

            def _pluck_overall(x):
                # Extract overall score from score_json string or dict
                if isinstance(x, str) and x.strip():
                    try:
                        obj = json.loads(x)
                        return obj.get("overall")
                    except Exception:
                        return None
                if isinstance(x, dict):
                    return x.get("overall")
                return None

            if not df.empty:
                # Normalize created_at (could be ISO string)
                if "created_at" in df.columns:
                    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

                # Derive overall_score if not already present
                if "overall_score" not in df.columns and "score_json" in df.columns:
                    df["overall_score"] = pd.to_numeric(df["score_json"].apply(_pluck_overall), errors="coerce")

                # Force any nested JSON-like columns to strings for Arrow safety
                for col in ["score_json", "breakdown", "recommendations"]:
                    if col in df.columns:
                        df[col] = df[col].apply(
                            lambda x: json.dumps(x, ensure_ascii=False)
                            if isinstance(x, (dict, list))
                            else ("" if x is None else str(x))
                        )

                # Provide a selection list by resume_hash
                if "resume_hash" in df.columns:
                    selected = st.selectbox(
                        "Select a Resume from history",
                        options=[""] + list(df["resume_hash"].astype(str).unique()),
                        index=0,
                        format_func=lambda x: x if not x or len(x) < 12 else f"{x[:6]}...{x[-6:]}"
                    )
                    if selected:
                        st.session_state.selected_resume_hash = selected
                        st.success(f"Selected Resume Hash: {selected}")
                else:
                    st.info("No resume hashes available to select.")

                # Choose a simple, flat view for the table
                cols_order = ["created_at", "job_role", "resume_hash", "jd_hash", "overall_score"]
                use_cols = [c for c in cols_order if c in df.columns]
                view = df[use_cols + [c for c in df.columns if c not in use_cols]]

                # Sort newest first if created_at exists
                if "created_at" in view.columns:
                    view = view.sort_values("created_at", ascending=False)

                st.dataframe(view, use_container_width=True)
            else:
                st.info("No history yet.")

    except Exception as e:
        st.error(f"⚠ {e}")

    st.markdown('</div>', unsafe_allow_html=True)

# === PAGE 1 — Upload JD ===
elif st.session_state.active_page == pages[1]:
    st.markdown("""
        <div class="hero">
            <div class="hero-content">
                <div class="hero-title">Job Description Ingestion</div>
                <div class="hero-subtitle">Upload or paste a JD to extract key skills and requirements.</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="card glass">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Upload or Paste JD</div>', unsafe_allow_html=True)

    jd_file = st.file_uploader("Upload JD (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])
    jd_text = st.text_area("Or paste JD here")

    if st.button("Submit JD"):
        try:
            if jd_file:
                files = {"jd_file": (jd_file.name, jd_file, jd_file.type)}
                res = requests.post(f"{BACKEND_URL}/upload_jobdesc", files=files, timeout=30)
            else:
                res = requests.post(f"{BACKEND_URL}/upload_jobdesc", data={"jd_text": jd_text}, timeout=30)

            if res.status_code == 200:
                st.success("✅ JD Parsed")
                st.json(res.json())
            else:
                st.error(f"Error {res.status_code}: {res.text}")
        except Exception as e:
            st.error(f"⚠ {e}")

    st.markdown('</div>', unsafe_allow_html=True)

# === PAGE 2 — Upload Resume & Get Score ===
elif st.session_state.active_page == pages[2]:
    st.markdown("""
        <div class="hero">
            <div class="hero-content">
                <div class="hero-title">AI‑Powered ATS Resume Scoring</div>
                <div class="hero-subtitle">Upload your resume, match it to a JD, and see a premium scorecard with insights.</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="card glass">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Upload & Configure</div>', unsafe_allow_html=True)

    resume_file = st.file_uploader("Upload Resume (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])
    job_role = st.text_input("Target Job Role", placeholder="e.g., Software Engineer")
    jd_text_opt = st.text_area("Optional: Paste Job Description")

    if st.button("Score Resume"):
        if not resume_file or not job_role.strip():
            st.warning("Please upload a resume and enter a job role.")
        else:
            try:
                files = {"resume": resume_file}
                data = {"job_role": job_role}
                if jd_text_opt.strip():
                    data["jd"] = jd_text_opt  # main.py currently uses latest cached JD; this is informational

                res = requests.post(f"{BACKEND_URL}/upload_resume", files=files, data=data, timeout=120)
                if res.status_code == 200:
                    parsed = res.json()
                    score = parsed.get("score", {})
                    # Ensure difference_from_benchmark is a simple object
                    if "difference_from_benchmark" in score:
                        score["difference_from_benchmark"] = {}

                    st.markdown('<div class="metric-grid">', unsafe_allow_html=True)
                    def metric(label, value):
                        st.markdown(f"""
                            <div class="metric-card">
                                <div class="metric-label">{label}</div>
                                <div class="metric-value">{value}</div>
                            </div>
                        """, unsafe_allow_html=True)

                    metric("Overall", score.get("overall", "—"))
                    metric("Keywords", score.get("keywords", "—"))
                    metric("Formatting", score.get("formatting", "—"))
                    metric("Grammar", score.get("grammar", "—"))
                    metric("JD Match", score.get("jd_match_details", {}).get("jd_match_score", "—"))
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown('<div class="chart-block mt-12">', unsafe_allow_html=True)
                    show_score_chart(score)
                    st.markdown('</div>', unsafe_allow_html=True)

                    jd_det = score.get("jd_match_details", {})
                    skills_required = jd_det.get("skills_required", 0)
                    skills_matched = jd_det.get("skills_matched", 0)
                    if skills_required > 0:
                        import plotly.express as px
                        pie_df = pd.DataFrame({
                            "Category": ["Matched Skills", "Missing Skills"],
                            "Count": [skills_matched, max(0, skills_required - skills_matched)]
                        })
                        pie_fig = px.pie(
                            pie_df, values="Count", names="Category",
                            title="Skills Coverage", hole=0.4,
                            color_discrete_sequence=["#22d3ee", "#f43f5e"]
                        )
                        st.plotly_chart(pie_fig, use_container_width=True)

                    exp_shortfall = jd_det.get(
                        "experience_shortfall_years",
                        score.get("jd_integration", {}).get("experience_shortfall_years", 0)
                    )

                    st.markdown('<div class="card glass mt-12">', unsafe_allow_html=True)
                    st.markdown('<div class="card-title">Recommendations</div>', unsafe_allow_html=True)

                    if skills_required:
                        st.write(f"🔹 Skills coverage: {skills_matched}/{skills_required} — Add the missing keywords from the JD.")
                    if exp_shortfall and exp_shortfall > 0:
                        st.write(f"🔹 Experience gap: {exp_shortfall} years — Add relevant internships/projects and quantify responsibilities.")
                    for tip in score.get("improvement_notes", []):
                        st.write(f"💡 {tip}")

                    st.markdown('</div>', unsafe_allow_html=True)

                    with st.expander("📜 Raw API Output"):
                        st.json(parsed)

                else:
                    st.error(f"Error {res.status_code}: {res.text}")

            except Exception as e:
                st.error(f"⚠ Could not connect to backend: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

# === PAGE 3 — Improvement Suggestions ===
elif st.session_state.active_page == pages[3]:
    st.markdown("""
        <div class="hero">
            <div class="hero-content">
                <div class="hero-title">Targeted Improvements</div>
                <div class="hero-subtitle">Identify missing skills, keywords, and get actionable tips.</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="card glass">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Fetch Suggestions</div>', unsafe_allow_html=True)
    resume_id = st.text_input(
        "Resume ID from history",
        value=st.session_state.get("selected_resume_hash", "")
    )
    fetch = st.button("Get Suggestions")
    st.markdown('</div>', unsafe_allow_html=True)

    if fetch and resume_id.strip():
        try:
            res = requests.get(f"{BACKEND_URL}/improve", params={"resume_hash": resume_id}, timeout=30)
            if res.status_code == 200:
                data = res.json()
                rec = data.get("recommendations", data)

                missing = rec.get("missing_keywords", []) or []
                fmt_warn = rec.get("format_suggestions", []) or rec.get("formatting_warnings", []) or []
                grammar = rec.get("grammar_issues", []) or []

                st.markdown('<div class="metric-grid">', unsafe_allow_html=True)
                def metric(label, value):
                    st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-label">{label}</div>
                            <div class="metric-value">{value}</div>
                        </div>
                    """, unsafe_allow_html=True)
                metric("Missing Keywords", len(missing))
                metric("Formatting Issues", len(fmt_warn))
                metric("Grammar Issues", len(grammar))
                st.markdown('</div>', unsafe_allow_html=True)

                if rec.get("resume_enhancement_tips"):
                    st.markdown('<div class="card glass mt-12">', unsafe_allow_html=True)
                    st.markdown('<div class="card-title">Actionable Tips</div>', unsafe_allow_html=True)
                    for tip in rec.get("resume_enhancement_tips", []):
                        st.write(f"💡 {tip}")
                    st.markdown('</div>', unsafe_allow_html=True)

                if missing:
                    st.markdown('<div class="card mt-12">', unsafe_allow_html=True)
                    st.markdown('<div class="card-title">Missing Keywords</div>', unsafe_allow_html=True)
                    st.write(", ".join([f"`{k}`" for k in missing]))
                    st.markdown('</div>', unsafe_allow_html=True)
                if fmt_warn:
                    st.markdown('<div class="card mt-12">', unsafe_allow_html=True)
                    st.markdown('<div class="card-title">Formatting</div>', unsafe_allow_html=True)
                    for w in fmt_warn:
                        st.write(f"🧩 {w}")
                    st.markdown('</div>', unsafe_allow_html=True)
                if grammar:
                    st.markdown('<div class="card mt-12">', unsafe_allow_html=True)
                    st.markdown('<div class="card-title">Grammar</div>', unsafe_allow_html=True)
                    for g in grammar:
                        st.write(f"✍️ {g}")
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.error(f"Error {res.status_code}: {res.text}")
        except Exception as e:
            st.error(f"⚠ API request failed: {e}")
    else:
        st.info("Enter a Resume ID and click Get Suggestions.")

# === PAGE 4 — Job Recommendations ===
elif st.session_state.active_page == pages[4]:
    st.markdown("""
        <div class="hero">
            <div class="hero-content">
                <div class="hero-title">Recommended Jobs</div>
                <div class="hero-subtitle">Find matching job roles from the database.</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="card glass">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Get Recommendations</div>', unsafe_allow_html=True)
    resume_id = st.text_input(
        "Resume ID from history",
        value=st.session_state.get("selected_resume_hash", "")
    )
    fetch = st.button("Fetch Jobs")
    st.markdown('</div>', unsafe_allow_html=True)

    if fetch and resume_id.strip():
        try:
            res = requests.get(f"{BACKEND_URL}/jobs/recommend", params={"resume_hash": resume_id}, timeout=30)
            if res.status_code == 200:
                data = res.json()
                jobs = data.get("recommendations", data if isinstance(data, list) else [])

                if not isinstance(jobs, list) or not jobs:
                    st.warning("No jobs returned.")
                else:
                    jobs_df = pd.DataFrame(jobs)

                    if not jobs_df.empty:
                        st.markdown('<div class="card mt-12">', unsafe_allow_html=True)
                        st.markdown('<div class="card-title">Jobs Table</div>', unsafe_allow_html=True)
                        st.dataframe(jobs_df, use_container_width=True)

                        csv_bytes = jobs_df.to_csv(index=False).encode("utf-8")
                        csv_filename = "suggested_jobs.csv"

                        st.download_button(
                            label="Download Jobs CSV",
                            data=csv_bytes,
                            file_name=csv_filename,
                            mime="text/csv",
                            help="Download the current job recommendations as CSV"
                        )
                        st.markdown('</div>', unsafe_allow_html=True)

                    for j in jobs:
                        st.markdown('<div class="card mt-12">', unsafe_allow_html=True)
                        title = j.get("title", "Role")
                        company = j.get("company", "Company")
                        location = j.get("location", "Location")
                        score = j.get("match_score", j.get("score", None))
                        skills_m = j.get("skills_matched", j.get("matched_skills", []))
                        skills_x = j.get("skills_missing", j.get("missing_skills", []))
                        url = j.get("url", j.get("job_url"))

                        st.markdown(f"<div class='card-title'>{title} — {company}</div>", unsafe_allow_html=True)
                        st.write(f"📍 {location}")

                        if score is not None:
                            st.markdown('<div class="metric-grid">', unsafe_allow_html=True)
                            st.markdown(f"""
                                <div class="metric-card">
                                    <div class="metric-label">Match Score</div>
                                    <div class="metric-value">{score}</div>
                                </div>
                            """, unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)

                        if skills_m:
                            st.write("✅ Matched:", ", ".join([f"`{s}`" for s in skills_m]))
                        if skills_x:
                            st.write("❗ Missing:", ", ".join([f"`{s}`" for s in skills_x]))

                        if url:
                            st.markdown(f"<a href='{url}' target='_blank'>Open job ↗</a>", unsafe_allow_html=True)

                        st.markdown('</div>', unsafe_allow_html=True)

            elif res.status_code == 404:
                st.error("Resume not found for the provided hash. Select from Dashboard and try again.")
            else:
                st.error(f"Error {res.status_code}: {res.text}")
        except Exception as e:
            st.error(f"⚠ API request failed: {e}")
    else:
        st.info("Enter a Resume ID and click Fetch Jobs.")

# === PAGE 5 — Reports / Export ===
elif st.session_state.active_page == pages[5]:
    st.markdown("""
        <div class="hero">
            <div class="hero-content">
                <div class="hero-title">Reports & Export</div>
                <div class="hero-subtitle">View analytics and export them for sharing or submission.</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # === KPIs Card (Real Analytics) ===
    st.markdown('<div class="card glass">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Key Metrics</div>', unsafe_allow_html=True)

    with st.spinner("Loading KPIs..."):
        try:
            r = requests.get(f"{BACKEND_URL}/reports/kpis", timeout=20)
            if r.status_code != 200:
                st.error(f"Error {r.status_code}: {r.text}")
            else:
                k = r.json()
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Resumes", k.get("total_resumes", 0))
                c2.metric("Total JDs", k.get("total_jds", 0))
                c3.metric("Avg Overall Score", k.get("avg_overall", 0.0))
                c4.metric("Runs (7 days)", k.get("recent_runs_7d", 0))
        except Exception as e:
            st.error(f"Failed to load KPIs: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

    # === Recent Overall Score Trend ===
    st.markdown('<div class="card mt-12">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Recent Overall Score Trend</div>', unsafe_allow_html=True)
    with st.spinner("Loading recent scores..."):
        try:
            r = requests.get(f"{BACKEND_URL}/reports/recent_scores", timeout=20)
            if r.status_code != 200:
                st.info("No recent score data available yet.")
            else:
                payload = r.json()
                rs = payload.get("recent_scores", [])
                if not rs:
                    st.info("No recent score data available yet.")
                else:
                    df_trend = pd.DataFrame(rs)
                    df_trend["timestamp"] = pd.to_datetime(df_trend["timestamp"], errors="coerce")
                    df_trend = df_trend.dropna(subset=["timestamp"]).sort_values("timestamp")
                    if df_trend.empty:
                        st.info("No valid timestamps to chart.")
                    else:
                        st.line_chart(df_trend.set_index("timestamp")["overall_score"])
        except Exception as e:
            st.error(f"Failed to load recent scores: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

    # === Recent Runs (Table + CSV) ===
    st.markdown('<div class="card mt-12">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Recent Scoring Runs</div>', unsafe_allow_html=True)
    with st.spinner("Loading recent runs..."):
        try:
            r = requests.get(f"{BACKEND_URL}/reports/recent_runs?limit=20", timeout=20)
            if r.status_code != 200:
                st.info("No recent runs available yet.")
            else:
                payload = r.json()
                recents = payload.get("recent_runs", [])
                if not recents:
                    st.info("No recent runs available yet.")
                else:
                    df_recent = pd.DataFrame(recents)

                    # Normalize types for Arrow and sorting
                    if "created_at" in df_recent.columns:
                        df_recent["created_at"] = pd.to_datetime(df_recent["created_at"], errors="coerce")
                    if "overall_score" in df_recent.columns:
                        df_recent["overall_score"] = pd.to_numeric(df_recent["overall_score"], errors="coerce")

                    cols_order = ["created_at", "resume_hash", "jd_hash", "job_role", "overall_score"]
                    use_cols = [c for c in cols_order if c in df_recent.columns]
                    df_recent = df_recent[use_cols + [c for c in df_recent.columns if c not in use_cols]]

                    if "created_at" in df_recent.columns:
                        df_recent = df_recent.sort_values("created_at", ascending=False)

                    st.dataframe(df_recent, use_container_width=True)

                    csv_bytes = df_recent.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="Download Recent Runs CSV",
                        data=csv_bytes,
                        file_name="recent_scoring_runs.csv",
                        mime="text/csv",
                        help="Download the recent scoring runs as CSV"
                    )
        except Exception as e:
            st.error(f"Failed to load recent runs: {e}")

    # === Average Category Scores (Pie) ===
    st.markdown('<div class="card mt-12">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Average Category Scores (Pie)</div>', unsafe_allow_html=True)

    with st.spinner("Loading category averages..."):
        try:
            r = requests.get(f"{BACKEND_URL}/reports/avg_categories", timeout=20)
            if r.status_code != 200:
                st.info("Category averages unavailable.")
            else:
                payload = r.json()
                avgs = payload.get("avg_categories", {})
                if not avgs:
                    st.info("Category averages unavailable.")
                else:
                    df_cat = pd.DataFrame(
                        [{"Category": k.capitalize(), "Value": float(v) if isinstance(v, (int, float)) else 0.0}
                         for k, v in avgs.items()]
                    )

                    try:
                        import plotly.express as px
                        fig = px.pie(
                            df_cat,
                            names="Category",
                            values="Value",
                            hole=0.25,
                            title=None
                        )
                        fig.update_traces(textposition="inside", textinfo="percent+label")
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception:
                        st.dataframe(df_cat, use_container_width=True)
        except Exception as e:
            st.error(f"Failed to load category averages: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

    # === Top Missing JD Skills ===
    st.markdown('<div class="card mt-12">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Top Missing JD Skills</div>', unsafe_allow_html=True)

    with st.spinner("Analyzing missing JD skills..."):
        try:
            r = requests.get(f"{BACKEND_URL}/reports/top_missing_jd_skills?limit=500&top=10", timeout=30)
            if r.status_code != 200:
                st.info("No data available to compute missing JD skills.")
            else:
                payload = r.json()
                rows = payload.get("top_missing_jd_skills", [])
                if not rows:
                    st.info("No missing JD skills detected in recent runs.")
                else:
                    df_miss = pd.DataFrame(rows)
                    if not df_miss.empty:
                        df_miss["Skill"] = df_miss["skill"].apply(lambda s: (s or "").capitalize())
                        df_miss = df_miss[["Skill", "count"]].rename(columns={"count": "Count"})
                        st.bar_chart(df_miss.set_index("Skill")["Count"])
        except Exception as e:
            st.error(f"Failed to load Top Missing JD Skills: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

# End of file