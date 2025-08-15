import re

# --- Industry detection maps ---
TITLE_TO_INDUSTRY = {
    "data scientist": "Data Science",
    "machine learning engineer": "Machine Learning",
    "ml engineer": "Machine Learning",
    "ai engineer": "Machine Learning",
    "data analyst": "Data Science",
    "business intelligence": "Data Science",
    "bi developer": "Data Science",
    "software engineer": "Software Engineering",
    "backend developer": "Backend Development",
    "backend engineer": "Backend Development",
    "frontend developer": "Frontend Development",
    "frontend engineer": "Frontend Development",
    "web developer": "Web Development",
    "full stack": "Web Development",
    "ui/ux": "UI/UX",
    "ux designer": "UI/UX",
    "ui designer": "UI/UX",
}

SKILL_TO_INDUSTRY = {
    # Data Science / ML
    "python": "Data Science",
    "machine learning": "Data Science",
    "deep learning": "Machine Learning",
    "sql": "Data Science",
    "pandas": "Data Science",
    "numpy": "Data Science",
    "scikit-learn": "Data Science",
    "mlops": "Machine Learning",
    # Web / Frontend
    "javascript": "Web Development",
    "react": "Frontend Development",
    "html": "Web Development",
    "css": "Web Development",
    "next.js": "Frontend Development",
    # Backend / Software
    "java": "Software Engineering",
    "c++": "Software Engineering",
    "spring": "Backend Development",
    "node": "Backend Development",
    "sql server": "Backend Development",
    # UI/UX
    "figma": "UI/UX",
    "adobe xd": "UI/UX",
    "wireframing": "UI/UX",
}

def infer_industry_from_title(title_text: str) -> str | None:
    """Try to detect industry from job title text."""
    if not title_text:
        return None
    t = title_text.lower()
    for key, ind in TITLE_TO_INDUSTRY.items():
        if key in t:
            return ind
    return None

def infer_industry_from_skills(skills: list[str]) -> str | None:
    """Try to detect industry from list of skills."""
    if not skills:
        return None
    votes = {}
    for s in skills:
        if not isinstance(s, str):
            continue
        k = s.lower().strip()
        ind = SKILL_TO_INDUSTRY.get(k)
        if ind:
            votes[ind] = votes.get(ind, 0) + 1
    if not votes:
        return None
    # choose the industry with the most skill matches
    return max(votes.items(), key=lambda x: x[1])[0]

def process_job_description(jd_text: str) -> dict:
    """
    Extract required skills, experience, degrees, and industry from a job description.
    Deterministic extraction (no AI yet) – can be later enhanced with LLM / taxonomy.
    """
    text_lower = jd_text.lower()

    # Simple hardcoded skill detection – later replace with skill taxonomy
    known_skills = [
        "python", "java", "c++", "c#", "javascript", "html", "css",
        "react", "node.js", "machine learning", "deep learning",
        "nlp", "sql", "power bi", "tableau", "aws", "azure", "docker"
    ]
    must_have_skills = sorted({skill.title() for skill in known_skills if skill in text_lower})

    # Experience requirement
    exp_match = re.search(r"(\d+)\+?\s+year", text_lower)
    experience_required = int(exp_match.group(1)) if exp_match else None

    # Degree requirement
    degree_keywords = ["bachelor", "master", "phd", "b.tech", "m.tech", "b.sc", "m.sc"]
    degrees_required = sorted({deg.title() for deg in degree_keywords if deg in text_lower})

    # --- Improved industry detection ---
    industry = None

    # First try from title in JD text
    industry = infer_industry_from_title(jd_text)

    # If still not found, try from must-have skills
    if not industry:
        industry = infer_industry_from_skills(must_have_skills)

    # Fallback if still None
    if not industry:
        industry = "Default"

    return {
        "must_have_skills": must_have_skills,
        "experience_required": experience_required,
        "degrees_required": degrees_required,
        "industry": industry
    }
