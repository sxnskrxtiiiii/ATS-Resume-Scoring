🔌 API Documentation
Base URL

Local: http://localhost:5000

Conventions

Content-Type: multipart/form-data for file uploads; application/json for JSON bodies.

Responses: JSON unless otherwise noted.

Timestamps: ISO 8601 (UTC) unless specified.

Authentication

Not required for local demo scope.

Endpoints
POST /upload_jobdesc

Purpose: Ingest a job description (file or raw text) and extract requirements.

Request

Form fields (one of):

jd_file: file (pdf, docx, txt)

jd_text: string

Response 200

json
{
  "jd_hash": "abc123...",
  "parsed": {
    "title": "Software Engineer",
    "skills": ["python","sql","streamlit"],
    "must_have_skills": ["python","sql"],
    "experience_years_required": 2
  }
}
Errors

400 invalid input

415 unsupported format

500 parse failure

POST /upload_resume

Purpose: Parse and score a resume; optionally match to a JD.

Request

Form fields:

resume: file (pdf, docx, txt) REQUIRED

job_role: string REQUIRED

jd: string OPTIONAL (raw JD text) — or backend may use most recent JD

Response 200

json
{
  "resume_hash": "rhash123...",
  "score": {
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
    "benchmark": {
      "overall_p50": 65,
      "overall_p75": 78
    }
  },
  "recommendations": {
    "missing_keywords": ["pandas","docker"],
    "format_suggestions": ["Use consistent bullet symbols"],
    "grammar_issues": []
  }
}
Errors

400 missing fields

415 unsupported format

500 processing/scoring error

GET /history

Purpose: Retrieve recent scoring runs.

Query params

limit: int (default 20)

offset: int (default 0)

resume_hash: string (optional filter)

Response 200

json
{
  "items": [
    {
      "created_at": "2025-08-15T16:21:03Z",
      "resume_hash": "rhash123...",
      "jd_hash": "jdhash456...",
      "job_role": "Software Engineer",
      "score_json": {
        "overall": 71,
        "keywords": 70,
        "formatting": 90,
        "grammar": 95,
        "jd_match_details": { "jd_match_score": 51 }
      }
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
GET /improve

Purpose: Get improvement suggestions for a previous run.

Query params

resume_hash: string REQUIRED

Response 200

json
{
  "recommendations": {
    "missing_keywords": ["pandas","docker"],
    "formatting_warnings": ["Uneven indentation in bullets"],
    "grammar_issues": [],
    "resume_enhancement_tips": [
      "Quantify achievements with metrics.",
      "Add a Projects section highlighting role-specific skills."
    ]
  }
}
Errors

404 resume not found

GET /jobs/recommend

Purpose: Recommend jobs from the database for a resume.

Query params

resume_hash: string REQUIRED

Response 200

json
{
  "recommendations": [
    {
      "title": "Data Engineer",
      "company": "Acme Corp",
      "location": "Remote",
      "match_score": 78,
      "skills_matched": ["python","sql"],
      "skills_missing": ["airflow","spark"],
      "url": "https://..."
    }
  ]
}
Errors

404 resume not found

Reports

6.1) GET /reports/kpis

Purpose: High-level KPIs for dashboard.

Response 200

json
{
  "total_resumes": 128,
  "total_jds": 57,
  "avg_overall": 72.4,
  "recent_runs_7d": 39
}
6.2) GET /reports/recent_scores

Purpose: Recent overall score timeseries.

Response 200

json
{
  "recent_scores": [
    { "timestamp": "2025-08-15T15:10:00Z", "overall_score": 71 }
  ]
}
6.3) GET /reports/recent_runs

Query params

limit: int (default 20)

Response 200

json
{
  "recent_runs": [
    {
      "created_at": "2025-08-15T16:21:03Z",
      "resume_hash": "rhash123...",
      "jd_hash": "jdhash456...",
      "job_role": "Software Engineer",
      "overall_score": 71
    }
  ]
}
6.4) GET /reports/avg_categories

Purpose: Average category scores.

Response 200

json
{
  "avg_categories": {
    "overall": 72.4,
    "keywords": 70.1,
    "formatting": 88.9,
    "grammar": 93.0
  }
}
6.5) GET /reports/top_missing_jd_skills

Query params

limit: int (default 500)

top: int (default 10)

Response 200

json
{
  "top_missing_jd_skills": [
    { "skill": "pandas", "count": 12 },
    { "skill": "docker", "count": 9 }
  ]
}
Error Format (general)
json
{
  "error": "Message describing what went wrong"
}
Notes
Consistency: Same resume content should yield identical scores across runs.

Caching: History endpoints may include cache-busting with a “_” timestamp in UI.

Limits: Adjust default limits/offsets in queries for pagination.