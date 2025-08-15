📑 JD Analysis & Matching
This document explains how job descriptions are ingested, normalized, and compared against resumes during scoring.

🔄 Ingestion Paths
File upload: PDF/DOCX/TXT via POST /upload_jobdesc (jd_file)

Text paste: raw JD text via POST /upload_jobdesc (jd_text)

Both paths produce:

jd_hash: deterministic ID derived from normalized JD text

requirements: structured fields used by the scorer

🧹 Normalization
Lowercasing and Unicode normalization

Remove boilerplate (EOE, legal disclaimers) where detectable

Split into sections: responsibilities, requirements, qualifications

Tokenize to extract noun phrases and skill phrases

🧠 Extraction (jd_analysis_agent.py)
must_have_skills: top skills explicitly required (e.g., “must have,” “required”)

desired_skills: nice-to-have terms (e.g., “preferred,” “plus”)

required_degree: e.g., bachelors/masters

min_years: minimum total relevant experience

role_title: primary title from JD

keywords: additional phrases relevant to optimization

Heuristics and NLP

Rule patterns (regex for “must have,” “required,” “years”)

Skill dictionaries/taxonomy

Simple NER/POS via spaCy/NLTK (if enabled)

Deduplication and lemmatization for robust matching

🔗 Matching Logic (with resume)
Skills coverage = intersection(resume.skills, JD.must_have_skills)

JD Match Score (example):

base = 100 * matched / max(1, len(must_have_skills))

desired bonus up to +10

Experience gap = max(0, min_years - resume.total_years)

Degree alignment = compare resume.education with required_degree

Keywords presence = coverage over keywords set

📦 Output Fields (used downstream)
jd_hash

requirements.skills (all)

must_have_skills

desired_skills

min_years

required_degree

role_title

keywords

🧪 API Response Example
json
{
  "jd_hash": "jdhash456...",
  "parsed": {
    "title": "Software Engineer",
    "skills": ["python","sql","docker"],
    "must_have_skills": ["python","sql"],
    "experience_years_required": 2,
    "education_required": "Bachelors"
  }
}
🧯 Edge Cases
Empty JD: return 400

Unstructured JD: fallback to simple token/keyword extraction

Overly long JD: cap tokens; keep top-N required skills

Duplicates: same jd_hash indicates identical content