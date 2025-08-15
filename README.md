# ATS Resume Scoring System

A consistent, deterministic ATS scoring system with resume/JD parsing, actionable recommendations, and a clean Streamlit UI.

✨ Key Features (Required Scope)

📄 Resume upload and parsing (PDF/DOCX/TXT)

📑 JD upload and requirement extraction

🎯 Deterministic ATS scoring with category breakdowns and confidence interval

💡 Recommendations: missing keywords, formatting, structure, experience alignment

📊 Visuals: metrics, skills pie, dashboards and reports

🗂️ Persistence of resumes/JDs/history and basic job recommendations

🚀 Quick Start

Prerequisites

Python 3.10+

.env configured (see docs/setup.md)

🎈Run locally

# bash
    pip install -r requirements.txt

# start backend API (http://localhost:5000)
    python main.py                   

# start frontend (http://localhost:8501)
    streamlit run streamlit_app/app.py  
    
🗂️ Repository Map

streamlit_app/

app.py

components.py

styles.css

agents/

resume_processing_agent.py

jd_analysis_agent.py

ats_scoring_agent.py

improvement_agent.py

visualization_agent.py

database/

db_config.py

db_operations.py

policies.py

samples/

resumes/

jds/

report/ (sample outputs, if any)

backups/

atsdb_dump/, atsdb_dump_YYYY-MM-DD-HH-MM-SS/atsdb

benchmarks.py

main.py

groq_client.py (if used for NLP tasks)

requirements.txt, Dockerfile, docker-compose.yml

README.md

📚 Documentation

docs/setup.md

docs/architecture.md

docs/api.md

docs/schema.md

docs/scoring.md

docs/jd_matching.md

docs/recommendations.md

docs/frontend.md

docs/reports.md

docs/testing.md

docs/troubleshooting.md

docs/performance.md

Quick links (GitHub will auto-link if files exist):

Setup & Installation: docs/setup.md

System Architecture: docs/architecture.md

API: docs/api.md

Database Schema: docs/schema.md

Scoring Algorithm: docs/scoring.md

JD Analysis: docs/jd_matching.md

Recommendations: docs/recommendations.md

Frontend Guide: docs/frontend.md

Reports: docs/reports.md

Testing & Demo: docs/testing.md

Troubleshooting: docs/troubleshooting.md

Performance: docs/performance.md

🧭 Demo

bash
# 1) Start backend
    python main.py

# 2) Start frontend
    streamlit run streamlit_app/app.py

# 3) In the UI
    Upload JD (paste or file)
    Upload Resume & Get Score (view metrics, pie, recommendations)
    Check Dashboard/Reports

🧮 Scoring Categories (weights)

Skills Match: 30%

Experience Relevance: 25%

Education Alignment: 15%

Format & Structure: 15%

Keyword Optimization: 15%

Determinism is ensured via fixed weights, stable parsing rules, and resume_hash tracking.

🖼️ Screenshots

images/dashboard.png

images/score_page.png

images/reports.png

🔒 Security & Privacy

Keep secrets in .env (never commit).

Store only necessary fields; avoid sensitive PII where possible.

Backups live under backups/ with timestamps.

✅ Feature Status

✅ Resume upload and parsing

✅ JD upload and parsing

✅ Deterministic scoring with breakdowns + confidence interval

✅ Recommendations

✅ Visualizations (metrics + skills pie)

✅ History and reports


