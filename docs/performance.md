🏎️ Performance Notes
Target performance requirements and observed timings for the ATS Resume Scoring System.

🎯 Targets (required)
Resume processing: <30s

Score calculation: <10s

Database queries: <2s

UI responsiveness: <3s per interaction

📏 Measurement Protocol
Environment: record CPU, RAM, OS, and DB location (local/remote).

Method:

Measure backend timings with per‑stage logs (ms) in main.py.

Measure DB query times using timing wrappers in db_operations.py.

Measure UI responsiveness by noting request start/end in Streamlit (or browser devtools).

Sample set:

Use 5 resumes from samples/resumes and 1–2 JDs from samples/jds.

🔬 Timing Template (fill these)
Environment

CPU: <e.g., 8‑core, 3.2GHz>

RAM: <e.g., 16GB>

OS: <e.g., Windows 11 / macOS 14 / Ubuntu 22.04>

DB: <e.g., local MongoDB 6.x>

Per‑stage timings (median across 5 runs)

PDF/DOCX parsing: XX ms

JD analysis: XX ms

Scoring (ats_scoring_agent): XX ms

Recommendations: XX ms

History insert (DB): XX ms

Reports queries (avg): XX ms

End‑to‑end (upload → response): XX ms

UI responsiveness

Dashboard load: XX ms

Score page render (post‑response): XX ms

Reports page render: XX ms

🧪 How to Measure (examples)
Backend (Python)

python
import time
t0=time.time()
# stage...
dt=int((time.time()-t0)*1000); print("stage=resume_parse ms=", dt)
DB operations

python
tq=time.time()
items = db.history.find({...}).limit(20).list()
print("query=history_recent ms=", int((time.time()-tq)*1000))
Streamlit (simple)

Log time before/after requests and compute delta.

Or open browser DevTools → Network tab and read request durations.

✅ Pass/Fail Summary
Create a small table once measured:

Resume processing: PASS/FAIL (X ms vs <30,000 ms)

Score calculation: PASS/FAIL (X ms vs <10,000 ms)

DB queries: PASS/FAIL (X ms vs <2,000 ms)

UI responsiveness: PASS/FAIL (X ms vs <3,000 ms)

⚙️ Optimization Tips (if needed)
Parsing: prefer text‑based PDFs; avoid heavy OCR paths.

Scoring: cache JD normalization; precompute skill dictionaries.

Database: add indexes on created_at, resume_hash, jd_hash; limit fields in list endpoints.

Reports: paginate and cap time windows; pre‑aggregate if needed.

UI: debounce repeated calls; avoid re‑parsing large payloads on rerun.