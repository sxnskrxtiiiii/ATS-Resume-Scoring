🛠️ Troubleshooting
Common issues, quick diagnostics, and fixes for the ATS Resume Scoring System.

🔌 Connectivity
Frontend can’t reach backend (CORS/404/timeout)

✅ Check BACKEND_URL in .env and in streamlit_app/app.py.

✅ Confirm backend is running: curl http://localhost:5000/history

✅ Ports clash? Close other services or change BACKEND_PORT.

Database connection refused

✅ Verify DB_URI and DB_NAME in .env.

✅ Ensure the DB server is running and accessible.

✅ Try a minimal connection script using database/db_config.py.

📄 File Handling
“Unsupported file type” on upload

✅ Only PDF/DOCX/TXT are supported in required scope.

✅ For PDFs, try re-saving; corrupted PDFs often fail text extraction.

Empty or garbled text from PDF

✅ Export the PDF as “PDF/A” or use a text-based version.

✅ If the file is scanned, OCR is out of required scope—use a text resume.

🧮 Scoring/Parsing
Scores differ for the same resume

✅ Ensure the same JD was used both times.

✅ Confirm you didn’t modify weights/configs between runs.

✅ Clear caches/restarts to avoid stale client payloads.

No pie chart for skills

✅ Check that JD must_have_skills > 0.

✅ Ensure jd_match_details is present in the response.

“Missing JD” warning

✅ Provide JD text in Upload Resume page or upload a JD first.

📊 History & Reports
History doesn’t update

✅ Refresh Dashboard; Streamlit caching may hold old data.

✅ Check backend logs for /history hits.

✅ Confirm db_operations.save_history ran (new created_at entry expected).

Reports look empty

✅ Run at least one scoring job to populate history.

✅ Verify indexes and aggregation queries in db_operations.py.

🐞 Backend Errors
500 during /upload_resume

✅ Check logs for which agent failed (resume_processing vs scoring).

✅ Test each step with smaller inputs (simple DOCX).

✅ Validate that parsed JSON has expected keys before scoring.

415 during upload

✅ Ensure multipart/form-data; field name must be “resume” or “jd_file”.

🧪 Quick Health Checks
Ping API

curl http://localhost:5000/history

Minimal score run

curl -F "resume=@samples/resumes/r1.pdf" -F "job_role=SE" http://localhost:5000/upload_resume

JD ingest

curl -F "jd_text=$(cat samples/jds/se.txt)" http://localhost:5000/upload_jobdesc

🔐 Environment & Config
Secrets in repo by mistake

✅ Rotate keys; add .env to .gitignore immediately.

Wrong environment variables loaded

✅ Print BACKEND_URL at app startup to confirm values.

✅ Restart both backend and Streamlit after edits.

🐳 Docker
Containers start but app 404s

✅ Confirm exposed ports map to host (e.g., 5000:5000, 8501:8501).

✅ BACKEND_URL inside Streamlit should point to the backend service name/port in compose.

🧯 Last‑Resort Steps
Clear Streamlit cache

streamlit cache clear (or rerun from menu)

Recreate venv

rm -rf venv && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt

Restart DB / re-seed samples

Ensure collections exist and sample data is present.