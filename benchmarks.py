# benchmarks.py

ROLE_BENCHMARKS = {
    "software engineer": {
        "overall": 75,
        "skills": 70,
        "experience": 65,
        "education": 70,
        "formatting": 80,
        "keywords": 72
    },
    "data analyst": {
        "overall": 72,
        "skills": 68,
        "experience": 60,
        "education": 65,
        "formatting": 78,
        "keywords": 70
    },
    "default": {
        "overall": 70,
        "skills": 65,
        "experience": 60,
        "education": 65,
        "formatting": 75,
        "keywords": 68
    }
}

def get_role_benchmark(job_role: str):
    """Return benchmarks for the given job role, or the default if not found."""
    if not job_role:
        return ROLE_BENCHMARKS["default"]

    role = job_role.strip().lower()
    return ROLE_BENCHMARKS.get(role, ROLE_BENCHMARKS["default"])
