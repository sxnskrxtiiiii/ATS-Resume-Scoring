🎯 Scoring Algorithm
This document explains how the ATS score is computed, how consistency is guaranteed, and how confidence and benchmarks are produced.

🧩 Category Weights
Skills Match: 30%

Experience Relevance: 25%

Education Alignment: 15%

Format & Structure: 15%

Keyword Optimization: 15%

Weighted overall score:
overall = 0.30skills + 0.25experience + 0.15education + 0.15format + 0.15*keywords

🔍 Feature Extraction (Inputs)
From resume_processing_agent:

skills_set, years_experience_total, roles, education_degrees, sections_present, formatting_signals (headings, bullets, length, whitespace), grammar_signals.

From jd_analysis_agent (if JD provided):

required_skills, must_have_skills, desired_skills, min_years, required_degree, keywords.

🧮 Category Computations
Skills Match (0–100)

matched = count(resume.skills ∩ JD.must_have_skills)

required = len(JD.must_have_skills)

base = 100 * matched / max(1, required)

bonus for desired_skills (capped): +min(10, 2*count(match_desired))

skills = clamp(base + bonus, 0, 100)

Experience Relevance (0–100)

years_gap = max(0, JD.min_years - resume.years_experience_total)

relevance_base = 100 - 12.5*years_gap (each missing year subtracts)

role_alignment bonus: +10 if any prior role title fuzzy‑matches job_role/JD title

experience = clamp(relevance_base + role_alignment, 0, 100)

Education Alignment (0–100)

degree_match = 100 if resume.degree ≥ required_degree else 70 if related field else 40

education = clamp(degree_match, 0, 100)

Format & Structure (0–100)

signals: headings_present, consistent_bullets, section_order, length_ok, contact_block_ok

start at 100, subtract per violation (e.g., -5 to -15 each)

formatting = clamp(100 - penalties, 0, 100)

Keyword Optimization (0–100)

keyword_set = required_skills ∪ important JD terms

density = occurrences_in_resume / max(1, len(keyword_set))

presence score (coverage): 100 * covered_keywords / max(1, len(keyword_set))

overstuffing guard: apply soft cap if term_frequency too high

keywords = clamp(presence - overstuffing_penalty, 0, 100)

🧪 Consistency Guarantee
Deterministic parsing: same libraries/configs and normalization steps.

Fixed weights: constants in ats_scoring_agent.py.

Stable tokenization/regex rules (no randomness).

Resume hash (resume_hash) ensures identical input → identical output; stored in history for verification.

📏 Benchmarks
benchmarks.py provides category/overall baselines (p50/p75 per role/industry if available).

difference_from_benchmark = overall - benchmark.overall_p50 (also per-category deltas if computed).

📐 Confidence Interval
Reflects extraction certainty and JD availability:

start width: 6 points

widen if: low text quality, missing sections, OCR flags, no JD provided

narrow if: high formatting quality, many matched skills

CI example: [0.68, 0.74] represents ±3 points around normalized 0–1 scale.

🧠 Recommendations Linkage
Missing keywords = JD.must_have_skills − resume.skills

Formatting tips = violations collected during formatting scoring

Grammar notes = grammar_signals

Experience gap = max(0, JD.min_years − resume.years_experience_total)

🧪 Example Output (score section)
json
{
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
}
🧯 Edge Cases
No JD provided: compute all categories; jd_match_details may have skills_required=0; pie may be skipped unless forced.

Corrupted/empty resumes: return 400 from API; do not score.

Extremely short resumes: clamp scores; CI widens.

Duplicate runs: allowed; history records each with created_at.