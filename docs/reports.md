📈 Reports & Analytics
This document describes the available reports, how they’re computed, and where they appear in the UI.

🧭 Reports Overview
KPIs snapshot

Recent scores (timeseries)

Recent runs (table)

Average category scores (aggregates)

Top missing JD skills (frequency list)

🔢 KPIs (/reports/kpis)
total_resumes: count(resumes)

total_jds: count(jds)

avg_overall: avg(history.score_json.overall)

recent_runs_7d: count(history where created_at > now-7d)

UI

Display as metric cards on Dashboard/Reports.

🕒 Recent Scores (/reports/recent_scores)
Output: [{ timestamp, overall_score }]

Source: history ordered by created_at desc

UI: line/area chart or simple table

📜 Recent Runs (/reports/recent_runs)
Fields: created_at, resume_hash, jd_hash, job_role, overall_score

Params: limit (default 20)

UI: table with pagination

📊 Average Categories (/reports/avg_categories)
Averages across history: overall, keywords, formatting, grammar

UI: small bar chart or KPI row

🔝 Top Missing JD Skills (/reports/top_missing_jd_skills)
Aggregates missing skills from jd_match_details.missing_skills

Params: limit (max records to scan), top (N skills to return)

UI: table or bar chart of skill → count

🧮 Example Aggregations (pseudocode)
avg_overall = AVG(history.score_json.overall)

recent_scores: SELECT created_at, score_json.overall ORDER BY created_at DESC LIMIT N

top_missing_jd_skills: UNWIND history.score_json.jd_match_details.missing_skills → COUNT BY skill → ORDER DESC → LIMIT top

🧪 Validation Tips
Spot check: run two recent resumes and confirm they appear in Recent Runs.

Ensure avg_overall updates after each new run.

Verify missing JD skills counts are plausible given current JDs.

🖥️ UI Placement
Reports page aggregates; Dashboard mirrors KPIs and a mini recent runs table.

Reply “next” to proceed to Step 11 (Testing & Demo Script).Step 11: Testing & Demo Script

Do this:

Create docs/testing.md.

Paste the content below and replace sample filenames with your actual samples.

docs/testing.md

🧪 Testing & Demo Script
This guide includes test cases, expected results, and a 10‑minute demo flow to validate the system.

✅ Test Data
samples/resumes/: r1.pdf, r2.pdf, r3.pdf, r4.pdf, r5.pdf

samples/jds/: se.txt, de.txt

🧪 Functional Test Cases (5)
Parse & Score — PDF resume

Input: r1.pdf, JD se.txt

Expect:

Resume parsed without error

Score response with overall and categories present

History entry created

Consistency Check — same resume twice

Input: r2.pdf with same JD

Steps: run twice

Expect:

identical overall and category scores

two history entries with same resume_hash

Missing JD — generic scoring

Input: r3.pdf without JD

Expect:

jd_match_details.skills_required = 0

pie chart hidden or message shown

recommendations limited to general tips

Weak Formatting — formatting penalties

Input: r4.pdf with inconsistent bullets

Expect:

formatting score noticeably lower

recommendation includes “Use consistent bullets”

Keyword Gap — must-have missing

Input: r5.pdf vs se.txt

Expect:

jd_match_details.missing_skills includes expected items

recommendations list missing keywords

jobs recommendations still populate

🧮 Performance Checks
Resume processing <30s

Score calculation <10s

DB queries <2s

UI interactions <3s

Record timings in docs/performance.md.

🧰 API Smoke Tests (curl)
Upload JD

bash
curl -F "jd_text=$(cat samples/jds/se.txt)" http://localhost:5000/upload_jobdesc
Upload Resume & Score

bash
curl -F "resume=@samples/resumes/r1.pdf" -F "job_role=Software Engineer" http://localhost:5000/upload_resume
Get History

bash
curl "http://localhost:5000/history?limit=10"
🎬 10‑Minute Live Demo Script
0:00–1:00 — Overview

State objective and core features.

1:00–3:00 — JD Upload

Upload se.txt, show parsed output and jd_hash.

3:00–6:00 — Resume Scoring

Upload r1.pdf, show metrics, pie, recommendations.

Open history to confirm new entry.

6:00–7:30 — Consistency

Re-run same resume; show identical scores.

7:30–9:00 — Reports

Show KPIs, recent runs, average categories, top missing JD skills.

9:00–10:00 — Wrap

Summarize guarantees (deterministic scoring) and privacy.

🧯 Troubleshooting During Demo
If pie doesn’t render, ensure JD must_have_skills > 0.

If history seems stale, refresh page or clear cache.

If backend unreachable, verify BACKEND_URL and server status.