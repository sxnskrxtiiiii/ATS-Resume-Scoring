🗃️ Database Schema
This document defines collections, key fields, indexes, and relationships used by the ATS Resume Scoring System.

📚 Collections Overview
resumes

jds

history

users (if applicable)

resumes
Purpose: Store parsed resume profiles and stable identifiers.

Example document

json
{
  "resume_hash": "rhash123...",         // PK, deterministic from content
  "original_filename": "final_resume.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 104432,
  "parsed": {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "phone": "+1-555-1234",
    "skills": ["python","sql","streamlit"],
    "experience": [
      { "title": "SWE", "company": "Acme", "years": 2, "details": ["Built X","Improved Y"] }
    ],
    "education": [
      { "degree": "B.Tech", "major": "CSE", "year": 2022, "school": "XYZ" }
    ],
    "certifications": []
  },
  "created_at": "2025-08-15T16:12:11Z"
}
Indexes

resume_hash (unique)

created_at (descending)

jds
Purpose: Store parsed job descriptions and extracted requirements.

Example document

json
{
  "jd_hash": "jdhash456...",            // PK, deterministic from text
  "title": "Software Engineer",
  "source": { "filename": "se_jd.txt" },
  "text": "We are hiring...",
  "requirements": {
    "skills": ["python","sql","docker"],
    "must_have_skills": ["python","sql"],
    "experience_years_required": 2,
    "education_required": "Bachelors"
  },
  "created_at": "2025-08-15T16:14:05Z"
}
Indexes

jd_hash (unique)

created_at (descending)

history
Purpose: Track each scoring run for auditing, analytics, and consistency checks.

Example document

json
{
  "created_at": "2025-08-15T16:21:03Z",
  "resume_hash": "rhash123...",
  "jd_hash": "jdhash456...",            // may be null/absent if no JD used
  "job_role": "Software Engineer",
  "score_json": {
    "overall": 71,
    "keywords": 70,
    "formatting": 90,
    "grammar": 95,
    "jd_match_details": {
      "jd_match_score": 51,
      "skills_required": 7,
      "skills_matched": 4,
      "missing_skills": ["pandas","docker","linux"]
    },
    "confidence_interval": [0.68, 0.74],
    "benchmark": { "overall_p50": 65, "overall_p75": 78 }
  },
  "recommendations": {
    "missing_keywords": ["pandas","docker"],
    "formatting_warnings": ["Use consistent bullets"],
    "grammar_issues": []
  },
  "runtime_ms": 6200,
  "version": "v1.0.0"
}
Indexes

created_at (descending)

resume_hash

jd_hash

job_role (optional, for reporting)

users (optional if sessions are required)
Purpose: Track authenticated users or sessions.

Example document

json
{
  "user_id": "u_abc123",
  "email": "user@example.com",
  "name": "User Name",
  "auth_provider": "local",
  "created_at": "2025-08-10T10:00:00Z",
  "last_login_at": "2025-08-15T17:20:00Z",
  "roles": ["user"]
}
Indexes

email (unique)

last_login_at

🔗 Relationships
history.resume_hash → resumes.resume_hash

history.jd_hash → jds.jd_hash

🧱 Field Types (typical)
*_hash: string

created_at: ISO8601 string or DB timestamp type

arrays: string[] or object[]

score_json: object (numeric fields: float/int)

🧰 Operational Policies
Retention: keep history for analytics; purge raw uploads if not needed.

Backups: periodic dumps under backups/ with timestamps.

Recovery: restore script should re-index collections post-import.

🏎️ Indexing Strategy
Time-series queries: created_at desc on history

Filtering by resume: index on resume_hash

Filtering by JD: index on jd_hash

Optional compound indexes for frequent dashboards (e.g., job_role + created_at)