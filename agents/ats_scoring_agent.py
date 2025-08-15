# agents/ats_scoring_agent.py
import os, json
from typing import List, Dict
from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, Field, ValidationError
from benchmarks import get_role_benchmark
from database.policies import policy

load_dotenv()

# === Industry Benchmarks for ATS scoring ===
# These are just example values; you can adjust based on research or testing.
INDUSTRY_BENCHMARKS = {
    "Data Science": 75,
    "Machine Learning": 78,
    "Web Development": 72,
    "Software Engineering": 74,
    "Frontend Development": 70,
    "Backend Development": 73,
    "UI/UX": 68,
    "Default": 70
}

# Industry-specific skill boosts (extra weight % per skill if industry matches)
INDUSTRY_SKILL_WEIGHTS = {
    "Data Science": {"python": 5, "machine learning": 5, "sql": 3},
    "Machine Learning": {"python": 5, "deep learning": 5, "mlops": 3},
    "Web Development": {"javascript": 5, "react": 4, "html": 2, "css": 2},
    "Software Engineering": {"java": 4, "python": 3, "c++": 3},
    "Frontend Development": {"javascript": 5, "react": 4, "css": 3},
    "Backend Development": {"python": 4, "java": 4, "sql": 4},
    "UI/UX": {"figma": 5, "adobe xd": 4, "wireframing": 3}
}

def get_industry_benchmark(industry: str) -> int:
    """Return the benchmark score for the given industry, or default if unknown."""
    if not industry:
        return INDUSTRY_BENCHMARKS["Default"]
    return INDUSTRY_BENCHMARKS.get(industry.strip(), INDUSTRY_BENCHMARKS["Default"])

# === Confidence Interval Calculation ===
def calculate_confidence_interval(score: float, data_points: int):
    """
    Return (lower_bound, upper_bound) for ATS confidence interval.
    Wider intervals for fewer data points.
    """
    if data_points <= 5:
        margin = 10  # very wide margin for low info
    elif data_points <= 10:
        margin = 7
    else:
        margin = 5
    return max(0, score - margin), min(100, score + margin)

class ScorePayload(BaseModel):
    overall: int = Field(ge=0, le=100)
    keywords: int = Field(ge=0, le=100)
    formatting: int = Field(ge=0, le=100)
    grammar: int = Field(ge=0, le=100)
    job_role: str

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
SYSTEM = "You are an ATS resume scoring expert that ONLY returns valid JSON matching the schema."

def _lower_set(items: List[str]) -> set:
    return set((i or "").strip().lower() for i in items if i and isinstance(i, str))

def _degree_match(resume_edu: str, jd_degrees: List[str]) -> float:
    if not resume_edu or not jd_degrees:
        return 0.0
    r = resume_edu.lower()
    jd = _lower_set(jd_degrees)
    # simple ladder
    levels = {
        "phd": 3, "doctorate": 3,
        "master": 2, "m.sc": 2, "mtech": 2, "m.tech": 2, "ms": 2,
        "bachelor": 1, "b.sc": 1, "btech": 1, "b.tech": 1, "be": 1,
    }
    def level(text: str) -> int:
        for k, v in levels.items():
            if k in text:
                return v
        return 0
    req_level = max((levels.get(k, 0) for k in jd), default=0)
    have_level = level(r)
    if have_level == 0 or req_level == 0:
        return 0.0
    # full if >= requirement, partial if one level below
    if have_level >= req_level:
        return 1.0
    if have_level == req_level - 1:
        return 0.6
    return 0.0

def _experience_match(resume_years: int, jd_required: int | None) -> float:
    if jd_required is None or jd_required <= 0:
        return 0.6  # neutral if JD doesn't specify
    if resume_years is None:
        return 0.0
    if resume_years >= jd_required:
        # cap diminishing returns
        return 1.0
    # partial credit by ratio
    ratio = max(0.0, min(1.0, resume_years / jd_required))
    return 0.4 + 0.6 * ratio  # avoid near-zero if close

def _skills_match(resume_skills: List[str], jd_skills: List[str]) -> tuple[float, int, int]:
    r = _lower_set(resume_skills)
    j = _lower_set(jd_skills)
    if not j:
        return 0.6, 0, 0  # neutral if JD skills missing
    overlap = len(r & j)
    coverage = overlap / max(1, len(j))
    return coverage, overlap, len(j)

# ----- New helpers for JD/industry boosts (policy-driven) -----
def _detect_industry(jd_parsed: Dict | None) -> str:
    txt = ((jd_parsed or {}).get("industry") or "").strip().lower()
    return txt or "unknown"

def _coverage_ratio(required: list, have: List[str]) -> float:
    req = [s.strip().lower() for s in (required or []) if isinstance(s, str)]
    have_set = {s.strip().lower() for s in (have or []) if isinstance(s, str)}
    return (len(set(req) & have_set) / max(1, len(req)))

def score_resume(parsed_resume: Dict, job_role: str, parsed_jd: Dict | None = None) -> Dict:
    # Deterministic JD-aware components
    jd_skills = []
    jd_degrees = []
    jd_exp_req = None
    if parsed_jd:
        jd_skills = parsed_jd.get("must_have_skills") or []
        jd_degrees = parsed_jd.get("degrees_required") or []
        jd_exp_req = parsed_jd.get("experience_required")

    skills_cov, matched_count, total_req = _skills_match(parsed_resume.get("skills", []), jd_skills)
    degree_cov = _degree_match(parsed_resume.get("education", "") or "", jd_degrees)
    exp_cov = _experience_match(parsed_resume.get("experience_years", 0), jd_exp_req)

    degree_requirement_met = False
    if jd_degrees:
        degree_requirement_met = degree_cov >= 1.0

    experience_shortfall_years = 0
    if jd_exp_req is not None and isinstance(jd_exp_req, (int, float)):
        ry = parsed_resume.get("experience_years", 0) or 0
        if ry < jd_exp_req:
            experience_shortfall_years = int(max(0, jd_exp_req - ry))

    # Compose deterministic JD match subscore
    jd_match = (skills_cov * 0.60 + exp_cov * 0.25 + degree_cov * 0.15) * 100
    jd_match = int(round(jd_match))

    # LLM category scoring
    schema = ScorePayload.model_json_schema()
    llm_prompt = (
        "Score the resume by rubric:\n"
        "- Overall match (0-100)\n- Keywords match (0-100)\n- Formatting (0-100)\n- Grammar (0-100)\n"
        "Return ONLY a JSON object with fields exactly as in the schema.\n\n"
        f"Schema:\n{json.dumps(schema, indent=2)}\n\n"
        f"Resume JSON:\n{json.dumps(parsed_resume, ensure_ascii=False)}\n\n"
        f"Target Job Role: {job_role}\n"
        f"Parsed JD (if present): {json.dumps(parsed_jd or {}, ensure_ascii=False)}\n"
        "Prioritize JD alignment when present."
    )

    try:
        resp = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": llm_prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        data = json.loads(content)
        payload = ScorePayload.model_validate(data).model_dump()
    except (json.JSONDecodeError, ValidationError, Exception):
        payload = {
            "overall": 70,
            "keywords": int(round(skills_cov * 100)),
            "formatting": 80,
            "grammar": 78,
            "job_role": job_role,
            "warning": "Fallback due to LLM/validation error"
        }

    # Blend JD match for stability
    overall_llm = payload.get("overall", 70)
    final_overall = int(round(0.60 * overall_llm + 0.40 * jd_match))
    payload["overall"] = final_overall

    # JD match details
    payload["jd_match_details"] = {
        "jd_match_score": jd_match,
        "skills_matched": matched_count,
        "skills_required": total_req,
        "skills_coverage": round(skills_cov * 100),
        "exp_alignment": round(exp_cov * 100),
        "degree_alignment": round(degree_cov * 100),
        "degree_requirement_met": degree_requirement_met,
        "experience_shortfall_years": experience_shortfall_years,
    }

    # JD-specific skill weighting (existing)
    '''jd_bonus_points = 0
    if parsed_jd and isinstance(parsed_jd, dict):
        jd_critical_skills = parsed_jd.get("must_have_skills") or []
        if jd_critical_skills:
            resume_skills = parsed_resume.get("skills", [])
            jd_norm = {s.lower().strip() for s in jd_critical_skills if isinstance(s, str)}
            res_norm = {s.lower().strip() for s in resume_skills if isinstance(s, str)}
            matched_critical = jd_norm & res_norm
            jd_bonus_points = min(8, 2 * len(matched_critical))
            if jd_bonus_points:
                final_overall = min(100, final_overall + jd_bonus_points)
                payload["overall"] = final_overall
                payload["jd_specific_boost_applied"] = jd_bonus_points'''

    # Industry boost (existing heuristic)
    '''industry_text = None
    if parsed_jd and isinstance(parsed_jd, dict):
        industry_text = parsed_jd.get("industry") or parsed_jd.get("job_family") or parsed_jd.get("domain")

    if industry_text:
        boosts = INDUSTRY_SKILL_WEIGHTS.get(industry_text.strip(), {})
        boost_points = 0
        for skill in parsed_resume.get("skills", []):
            if isinstance(skill, str) and skill.lower() in boosts:
                boost_points += boosts[skill.lower()]
        if boost_points:
            final_overall = min(100, final_overall + boost_points)
            payload["overall"] = final_overall
            payload["industry_boost_applied"] = boost_points'''

    # ----- Policy-driven boosts (new; conservative and capped) -----
    industry_detected = _detect_industry(parsed_jd)
    industry_boost_policy = 0
    jd_specific_boost_policy = 0

    # Industry policy boost if any of the industry keywords are present in resume skills
    if industry_detected in policy.get("industries", {}):
        ind = policy["industries"][industry_detected]
        ind_keywords = set(k.lower() for k in ind.get("keywords", []))
        resume_skillset = set(s.lower() for s in parsed_resume.get("skills", []) if isinstance(s, str))
        if ind_keywords & resume_skillset:
            industry_boost_policy = int(ind.get("boost", 0))

    # JD-specific boosts from policy
    must_have = (parsed_jd or {}).get("must_have_skills", [])
    coverage = _coverage_ratio(must_have, parsed_resume.get("skills", []))
    if coverage >= 0.7:
        jd_specific_boost_policy += int(policy["jd_specific"].get("must_have_skills_match", 0))

    jd_deg_required = (parsed_jd or {}).get("degrees_required")
    resume_deg_text = (parsed_resume.get("education") or "").lower()
    if isinstance(jd_deg_required, list) and jd_deg_required:
        if any(isinstance(d, str) and d.lower() in resume_deg_text for d in jd_deg_required):
            jd_specific_boost_policy += int(policy["jd_specific"].get("degree_required_match", 0))

    jd_exp_req_policy = (parsed_jd or {}).get("experience_required")
    resume_exp_years = parsed_resume.get("experience_years")
    if isinstance(jd_exp_req_policy, int) and isinstance(resume_exp_years, (int, float)):
        if resume_exp_years >= jd_exp_req_policy:
            jd_specific_boost_policy += int(policy["jd_specific"].get("exp_meets_or_exceeds", 0))

    # Apply policy boosts carefully (cap at 100)
    if industry_boost_policy or jd_specific_boost_policy:
        final_overall = min(100, int(final_overall) + industry_boost_policy + jd_specific_boost_policy)
        payload["overall"] = final_overall
        # Keep visibility on both: existing heuristic boost and policy boost can coexist
        payload["industry_boost_applied"] = payload.get("industry_boost_applied", 0) + industry_boost_policy
        payload["jd_specific_boost_applied"] = payload.get("jd_specific_boost_applied", 0) + jd_specific_boost_policy

    # === Benchmark integration ===
    _ = get_role_benchmark(job_role)  # retained for future use
    no_experience = not parsed_resume.get("experience_years")
    no_education = not parsed_resume.get("education")

    payload["difference_from_benchmark"] = {}
    print("DEBUG: difference_from_benchmark set to empty in score_resume()")

    # Suggestions
    if no_experience:
        payload.setdefault("improvement_notes", []).append(
            "Add relevant work or project experience to strengthen your resume and improve your score against industry benchmarks."
        )
    if no_education:
        payload.setdefault("improvement_notes", []).append(
            "Include your education details to improve benchmark comparisons."
        )

    # Confidence interval
    # matched_count is already an int; use it directly
    sections_present = 0
    if parsed_resume.get("skills"):
        sections_present += 1
    if parsed_resume.get("education"):
        sections_present += 1
    if parsed_resume.get("experience_years") is not None:
        sections_present += 1
    data_points = matched_count + sections_present

    ci_low, ci_high = calculate_confidence_interval(final_overall, data_points)
    payload["confidence_interval"] = [round(ci_low, 1), round(ci_high, 1)]

    # JD summary (augment with policy-driven details)
    payload["jd_integration"] = {
        "industry_detected": industry_detected.title() if isinstance(industry_detected, str) and industry_detected else "Unknown",
        "jd_specific_boost_applied": payload.get("jd_specific_boost_applied", 0),
        "industry_boost_applied": payload.get("industry_boost_applied", 0),
        "degree_requirement_met": payload["jd_match_details"].get("degree_requirement_met"),
        "experience_shortfall_years": payload["jd_match_details"].get("experience_shortfall_years")
    }

    return payload
