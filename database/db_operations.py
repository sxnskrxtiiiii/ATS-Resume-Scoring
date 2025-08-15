import os
import json
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

# ✅ Read MONGO_URI from environment (Docker Compose sets this)
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb:27017/atsdb")
client = MongoClient(MONGO_URI)
db = client.get_database()  # Will use the DB from the URI

# Collections
resumes = db["resumes"]
jobdescs = db["jobdescs"]
scores = db["scores"]
jobs = db["jobs"]

# Indexes (idempotent; safe to call at startup)
resumes.create_index([("hash", ASCENDING)], unique=True)
jobdescs.create_index([("hash", ASCENDING)], unique=True)
scores.create_index([("resume_hash", ASCENDING), ("jd_hash", ASCENDING)], unique=True)
scores.create_index([("created_at", DESCENDING)])
scores.create_index([("resume_hash", ASCENDING)])
scores.create_index([("jd_hash", ASCENDING)])
jobs.create_index([("status", ASCENDING)])

def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()

def upsert_resume(parsed_resume: Dict[str, Any], user_id: Optional[str] = None, session_id: Optional[str] = None) -> str:
    raw_text = parsed_resume.get("raw_text", "")
    r_hash = sha256_text(raw_text)
    doc = {
        "hash": r_hash,
        "file_name": parsed_resume.get("file_name"),
        "user_id": user_id,
        "session_id": session_id,
        "email": parsed_resume.get("email"),
        "education": parsed_resume.get("education"),
        "experience_years": parsed_resume.get("experience_years"),
        "skills": parsed_resume.get("skills", []),
        "raw_text": raw_text,
        "parsed_json": parsed_resume,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    try:
        resumes.update_one({"hash": r_hash}, {"$setOnInsert": doc}, upsert=True)
    except PyMongoError as e:
        print("Resume upsert error:", e)
    return r_hash

def upsert_jobdesc(parsed_jd: Dict[str, Any], jd_text: str, user_id: Optional[str] = None, session_id: Optional[str] = None) -> str:
    j_hash = sha256_text(jd_text or json.dumps(parsed_jd))
    doc = {
        "hash": j_hash,
        "user_id": user_id,
        "session_id": session_id,
        "jd_text": jd_text,
        "parsed_json": parsed_jd,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    try:
        jobdescs.update_one({"hash": j_hash}, {"$setOnInsert": doc}, upsert=True)
    except PyMongoError as e:
        print("JD upsert error:", e)
    return j_hash

def get_cached_score(resume_hash: str, jd_hash: Optional[str]) -> Optional[Dict[str, Any]]:
    q = {"resume_hash": resume_hash, "jd_hash": jd_hash}
    row = scores.find_one(q, {"_id": 0})
    return row.get("score_json") if row else None

def save_score(resume_hash: str, jd_hash: Optional[str], job_role: str, score_json: Dict[str, Any],
               user_id: Optional[str] = None, session_id: Optional[str] = None) -> None:
    doc = {
        "resume_hash": resume_hash,
        "jd_hash": jd_hash,
        "job_role": job_role,
        "score_json": score_json,
        "user_id": user_id,
        "session_id": session_id,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    scores.update_one(
        {"resume_hash": resume_hash, "jd_hash": jd_hash},
        {"$set": doc},
        upsert=True
    )

def get_scoring_history(limit: int = 10, resume_hash: str = None) -> List[Dict[str, Any]]:
    match_stage = {}
    if resume_hash:
        match_stage["resume_hash"] = resume_hash

    pipeline = []
    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline += [
        {"$sort": {"created_at": -1}},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "resumes",
                "localField": "resume_hash",
                "foreignField": "hash",
                "as": "resume_data"
            }
        },
        {"$unwind": {"path": "$resume_data", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "jobdescs",
                "localField": "jd_hash",
                "foreignField": "hash",
                "as": "jd_data"
            }
        },
        {"$unwind": {"path": "$jd_data", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "_id": 0,
                "created_at": 1,
                "job_role": 1,
                "score_json": 1,
                "resume_file": "$resume_data.file_name",
                "resume_email": "$resume_data.email",
                "jd_hash": 1,
                "resume_hash": 1,
                "jd_industry": "$jd_data.parsed_json.industry",
                "jd_skills": "$jd_data.parsed_json.must_have_skills"
            }
        }
    ]
    return list(scores.aggregate(pipeline))

def get_resume_by_hash(resume_hash: str) -> Optional[Dict[str, Any]]:
    return resumes.find_one({"hash": resume_hash}, {"_id": 0})

def get_jobdesc_by_hash(jd_hash: str) -> Optional[Dict[str, Any]]:
    return jobdescs.find_one({"hash": jd_hash}, {"_id": 0})

def delete_resume_by_hash(resume_hash: str) -> bool:
    scores.delete_many({"resume_hash": resume_hash})
    result = resumes.delete_one({"hash": resume_hash})
    return result.deleted_count > 0

def insert_job(job: Dict[str, Any]) -> str:
    job["skills"] = [s.strip().lower() for s in job.get("skills", []) if isinstance(s, str)]
    job["created_at"] = datetime.utcnow()
    job["status"] = job.get("status", "open")
    res = jobs.insert_one(job)
    return str(res.inserted_id)

def find_recommended_jobs(
    resume_skills: list,
    resume_degree: str = None,
    resume_exp_years: int = None,
    limit: int = 5,
    min_overlap: int = 2,
    must_have_skills: list = None,
    weight_skills: int = 3,
    weight_degree: int = 1,
    weight_experience: int = 1,
    require_degree: bool = False
) -> list:
    """
    Find recommended jobs based on skill overlap, degree, and experience.
    Supports customizable matching criteria and scoring weights.
    """
    # ✅ Normalize input skills and must-have list to lowercase
    resume_skills = {s.strip().lower() for s in resume_skills if isinstance(s, str)}
    must_have_skills = must_have_skills or []
    must_have_skills = {s.strip().lower() for s in must_have_skills if isinstance(s, str)}

    def degree_rank(deg):
        if not deg: return -1
        d = deg.strip().lower()
        if "phd" in d or "ph.d" in d or "doctor" in d: return 3
        if "master" in d or "m.e" in d or "m.tech" in d or "m.sc" in d or "msc" in d: return 2
        if "bachelor" in d or "b.e" in d or "b.tech" in d or "bsc" in d or "b.sc" in d: return 1
        if "diploma" in d: return 0
        return -1

    resume_deg_rank = degree_rank(resume_degree)

    # Lowercase job skills before intersection in pipeline
    pipeline = [
        {"$match": {"status": "open"}},
        {
            "$addFields": {
                "skills": {
                    "$map": {
                        "input": "$skills",
                        "as": "skill",
                        "in": {"$toLower": "$$skill"}
                    }
                }
            }
        },
        {
            "$addFields": {
                "matched_skills": {"$setIntersection": ["$skills", list(resume_skills)]},
                "match_count": {"$size": {"$setIntersection": ["$skills", list(resume_skills)]}},
            }
        },
        {
            "$project": {
                "_id": 0,
                "title": 1,
                "company": 1,
                "location": 1,
                "skills": 1,
                "matched_skills": 1,
                "match_count": 1,
                "description": 1,
                "degree_required": 1,
                "min_experience": 1,
                "created_at": 1
            }
        }
    ]

    results = list(jobs.aggregate(pipeline))

    enhanced = []
    for job in results:
        # 1️⃣ Filter by minimum skills overlap
        if job.get("match_count", 0) < min_overlap:
            continue

        # 2️⃣ Normalize job skills to lowercase for must-have check
        job_skills_lower = {s.lower() for s in job.get("skills", []) if isinstance(s, str)}

        # 3️⃣ Apply must-have filter (case-insensitive)
        if must_have_skills and not must_have_skills.issubset(job_skills_lower):
            continue

        # 4️⃣ Degree matching & bonus
        job_deg_rank = degree_rank(job.get("degree_required"))
        degree_bonus = 0
        if resume_deg_rank >= 0 and job_deg_rank >= 0 and resume_deg_rank >= job_deg_rank:
            degree_bonus = weight_degree
        if require_degree and degree_bonus == 0:
            continue  # skip if require_degree is true but no degree match

        # 5️⃣ Experience bonus
        job_min_exp = job.get("min_experience")
        exp_bonus = 0
        if isinstance(resume_exp_years, int) and isinstance(job_min_exp, (int, float)) and resume_exp_years >= job_min_exp:
            exp_bonus = weight_experience

        # 6️⃣ Calculate composite score
        base_score = weight_skills * int(job.get("match_count", 0))
        job["degree_bonus"] = degree_bonus
        job["exp_bonus"] = exp_bonus
        job["composite_score"] = base_score + degree_bonus + exp_bonus

        enhanced.append(job)

    # Sort primarily by composite_score, then match_count, then created_at desc
    enhanced.sort(key=lambda j: (j.get("composite_score", 0), j.get("match_count", 0), j.get("created_at")), reverse=True)

    return enhanced[:limit]
