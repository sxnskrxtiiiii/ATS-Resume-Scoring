🧩 System Architecture
This document describes the core components (required scope only), their responsibilities, and how data flows through the ATS Resume Scoring System.

📦 Components Overview
Streamlit Frontend (streamlit_app/)

app.py: page routing and UI

components.py: chart/metric helpers

styles.css: custom styling

Backend API (main.py)

Endpoints: /upload_jobdesc, /upload_resume, /history, /improve, /jobs/recommend, /reports/*

Agents (agents/)

resume_processing_agent.py: parse PDF/DOCX/TXT → structured JSON

jd_analysis_agent.py: extract JD requirements and skills

ats_scoring_agent.py: deterministic scoring, weights, CI, benchmarks

improvement_agent.py: suggestions (keywords, formatting, structure, skill gaps)

visualization_agent.py: helper summaries for UI visuals

Database (database/)

db_config.py: connection settings

db_operations.py: CRUD for resumes, JDs, history, users; report queries

policies.py: data/privacy rules

Benchmarks (benchmarks.py)

Industry/category baseline targets used by the scorer

Samples & Backups

samples/: example resumes and JDs

backups/: database dumps for recovery

🔀 High-Level Data Flow
JD Ingestion

UI → POST /upload_jobdesc

Backend → jd_analysis_agent → db_operations.store_jd → response with jd_hash

Resume Scoring

UI → POST /upload_resume (resume file, job_role, optional JD text)

Backend pipeline:

resume_processing_agent → JSON resume profile

jd_analysis_agent → JD requirements (if provided or existing)

ats_scoring_agent → score breakdown + confidence + benchmarks

improvement_agent → actionable recommendations

db_operations.save_history → persist run (resume_hash, jd_hash, score_json)

Response → UI renders metrics, pie chart, and recommendations

History & Reports

UI → GET /history and /reports/*

Backend → db_operations.query_* → aggregations (KPIs, trends, averages, missing JD skills)

UI → tables and charts

Job Recommendations

UI → GET /jobs/recommend?resume_hash=...

Backend → db_operations.find_relevant_jobs → return ranked jobs

UI → jobs table + CSV download

Consistency

Same resume content → same score (fixed weights, deterministic parsing, stable NLP settings)

History links runs by resume_hash for verification

🧮 Scoring Categories (Weights)
Skills Match: 30%

Experience Relevance: 25%

Education Alignment: 15%

Format & Structure: 15%

Keyword Optimization: 15%

Confidence interval reflects feature extraction certainty and benchmark deviation.

🗃️ Persistence Model (Collections)
resumes: parsed resume profiles, hash keys

jds: parsed job descriptions, requirements

history: scoring runs with score_json and timestamps

users: session/account data (if applicable)

Suggested Indexes:

history: created_at (desc), resume_hash, jd_hash

resumes: resume_hash

jds: jd_hash

🖼️ Architecture Diagram
Add this image to your repo and reference it here:

images/architecture_required.png

Example embed (GitHub-flavored Markdown):
![System Architecture](../images/architecture_required & Privacy Notes

Scope: store only necessary fields; avoid sensitive PII where possible.

Access: restrict DB credentials via .env; never commit secrets.

Backups: store dumps under backups/ with timestamps; verify restore steps.

🧭 Request Lifecycles (Sequence)
Upload Resume → Score → Save → Visualize

Frontend uploads resume (and optional JD)

Backend parses resume and JD, scores, generates tips

History entry persists with score_json

Frontend shows metrics, pie, recommendations

Dashboard/Reports

Frontend queries history/reports

Backend aggregates from DB

Frontend renders tables/charts