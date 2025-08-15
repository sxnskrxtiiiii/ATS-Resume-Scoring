import os
import re
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from agents.resume_processing_agent import process_resume
from agents.ats_scoring_agent import score_resume
from agents.jd_analysis_agent import process_job_description

# Stopwords list
STOPWORDS = set("""
a an the and or but if while with without within into onto from to of for in on at by as is are was were be been being
this that those these it its your you we they them our their there here
""".split())


def tokenize(text: str):
    text = (text or "").lower()
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9\.\-\+\#]*", text)
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]


def top_keywords(text: str, topk=20):
    tokens = tokenize(text)
    freq = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:topk]]


def normalize_list(ls):
    return sorted({(s or "").strip().lower() for s in (ls or []) if isinstance(s, str)})

# Import DB ops
from database.db_operations import (
    upsert_resume,
    upsert_jobdesc,
    get_cached_score,
    save_score,
    get_scoring_history,
    get_resume_by_hash,
    delete_resume_by_hash,
    insert_job,
    find_recommended_jobs,
    get_jobdesc_by_hash
)

app = Flask(__name__)

# Upload folder
UPLOAD_FOLDER = "samples"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Upload settings
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

# Cache for latest JD
LATEST_JD_HASH = None
LATEST_JD_PARSED = None


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({"error": "File too large (max 5MB)"}), 413


# ===========================
# Upload Resume
# ===========================
@app.route("/upload_resume", methods=["POST"])
def upload_resume():
    if "resume" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["resume"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type (pdf, docx, txt allowed)"}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    job_role = (request.form.get("job_role") or "").strip()
    if not job_role:
        return jsonify({"error": "Job role is required"}), 400

    user_id = (request.form.get("user_id") or "").strip() or None
    session_id = (request.form.get("session_id") or "").strip() or None

    try:
        parsed_resume = process_resume(file_path)
        resume_hash = upsert_resume(parsed_resume, user_id=user_id, session_id=session_id)
        print(f"resume_hash: {resume_hash}", flush=True)

        jd_hash = LATEST_JD_HASH
        parsed_jd = LATEST_JD_PARSED

        cached_score = get_cached_score(resume_hash, jd_hash)
        if cached_score:
            return jsonify({
                "status": "success",
                "parsed": parsed_resume,
                "score": cached_score,
                "using_jd": bool(parsed_jd),
                "cache": True,
                "resume_hash": resume_hash,
                "jd_hash": jd_hash
            }), 200

        score = score_resume(parsed_resume, job_role, parsed_jd=parsed_jd)
        save_score(resume_hash, jd_hash, job_role, score, user_id=user_id, session_id=session_id)
        score["difference_from_benchmark"] = {}

        return jsonify({
            "status": "success",
            "parsed": parsed_resume,
            "score": score,
            "using_jd": bool(parsed_jd),
            "cache": False,
            "resume_hash": resume_hash,
            "jd_hash": jd_hash
        }), 200

    except Exception as e:
        return jsonify({"error": "Processing failed", "detail": str(e)}), 500


# ===========================
# Upload Job Description
# ===========================
@app.route("/upload_jobdesc", methods=["POST"])
def upload_jobdesc():
    global LATEST_JD_HASH, LATEST_JD_PARSED
    jd_text = ""

    if 'jd_file' in request.files:
        jd_file = request.files['jd_file']
        jd_text = jd_file.read().decode('utf-8', errors='ignore')
    else:
        jd_text = request.form.get('jd_text', '')

    jd_text = jd_text.strip()
    if not jd_text:
        return jsonify({"error": "Job description text is required"}), 400

    user_id = (request.form.get("user_id") or "").strip() or None
    session_id = (request.form.get("session_id") or "").strip() or None

    try:
        parsed_jd = process_job_description(jd_text)
        jd_hash = upsert_jobdesc(parsed_jd, jd_text, user_id=user_id, session_id=session_id)

        LATEST_JD_HASH = jd_hash
        LATEST_JD_PARSED = parsed_jd

        return jsonify({
            "status": "success",
            "parsed_jd": parsed_jd,
            "jd_hash": jd_hash
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================
# Resume CRUD
# ===========================
@app.route("/resumes/<resume_hash>", methods=["GET"])
def get_resume_endpoint(resume_hash):
    try:
        doc = get_resume_by_hash(resume_hash)
        if not doc:
            return jsonify({"status": "not_found", "message": "Resume not found"}), 404
        return jsonify({"status": "success", "resume": doc}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/resumes/<resume_hash>", methods=["DELETE"])
def delete_resume_endpoint(resume_hash):
    try:
        deleted = delete_resume_by_hash(resume_hash)
        if not deleted:
            return jsonify({"status": "not_found", "message": "Resume not found"}), 404
        return jsonify({"status": "success", "message": "Resume and related scores deleted"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===========================
# Recommend Jobs
# ===========================
@app.route("/jobs/recommend", methods=["GET"])
def recommend_jobs():
    try:
        resume_hash = request.args.get("resume_hash")
        if not resume_hash:
            return jsonify({"status": "error", "message": "resume_hash is required"}), 400

        resume_doc = get_resume_by_hash(resume_hash)
        if not resume_doc:
            return jsonify({"status": "error", "message": "Resume not found"}), 404

        # 🔹 Try to get jd_hash from history if not provided
        jd_hash = request.args.get("jd_hash")
        if not jd_hash:
            history = get_scoring_history(limit=1, resume_hash=resume_hash)
            if isinstance(history, list) and history:
                first = history[0]
                if isinstance(first, dict) and first.get("jd_hash"):
                    jd_hash = first["jd_hash"]

        resume_skills = resume_doc.get("skills", [])
        resume_degree = resume_doc.get("education")
        resume_exp_years = resume_doc.get("experience_years")

        if not resume_skills:
            return jsonify({"status": "error", "message": "No skills found in resume"}), 400

        # Matching criteria
        limit = int(request.args.get("limit", 5))
        min_overlap = int(request.args.get("min_overlap", 2))

        must_have_skills_param = request.args.get("must_have_skills", "")
        must_have_skills = [
            s.strip().lower()
            for s in must_have_skills_param.split(",")
            if s.strip()
        ]

        weight_skills = int(request.args.get("weight_skills", 3))
        weight_degree = int(request.args.get("weight_degree", 1))
        weight_experience = int(request.args.get("weight_experience", 1))

        require_degree = request.args.get("require_degree", "false").lower() == "true"

        recommended = find_recommended_jobs(
            resume_skills=resume_skills,
            resume_degree=resume_degree,
            resume_exp_years=resume_exp_years,
            limit=limit,
            min_overlap=min_overlap,
            must_have_skills=must_have_skills,
            weight_skills=weight_skills,
            weight_degree=weight_degree,
            weight_experience=weight_experience,
            require_degree=require_degree
        )

        return jsonify({
            "status": "success",
            "resume_hash": resume_hash,
            "jd_hash": jd_hash,
            "total_recommended": len(recommended),
            "recommendations": recommended
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===========================
# Job CRUD
# ===========================
@app.route("/jobs", methods=["GET"])
def list_jobs():
    try:
        from database.db_operations import jobs
        job_list = list(jobs.find({}))
        for job in job_list:
            job["_id"] = str(job["_id"])
        return jsonify({"status": "success", "jobs": job_list}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


from bson import ObjectId


@app.route("/jobs/<job_id>", methods=["DELETE"])
def delete_job(job_id):
    try:
        from database.db_operations import jobs
        if not ObjectId.is_valid(job_id):
            return jsonify({"status": "error", "message": "Invalid job ID format"}), 400

        result = jobs.delete_one({"_id": ObjectId(job_id)})
        if result.deleted_count == 0:
            return jsonify({"status": "not_found", "message": "Job not found"}), 404

        return jsonify({"status": "success", "message": "Job deleted"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/jobs", methods=["POST"])
def create_job():
    try:
        if not request.is_json:
            return jsonify({"status": "error", "message": "Expected application/json body"}), 400

        data = request.get_json(force=True) or {}
        required = ["title", "company", "location", "skills", "description"]
        missing = [k for k in required if not data.get(k)]
        if missing:
            return jsonify({"status": "error", "message": f"Missing required fields: {', '.join(missing)}"}), 400

        skills = data.get("skills")
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        elif not isinstance(skills, list):
            return jsonify({"status": "error", "message": "skills must be a list or comma-separated string"}), 400

        job_doc = {
            "title": data["title"],
            "company": data["company"],
            "location": data["location"],
            "skills": skills,
            "description": data["description"],
            "min_experience": data.get("min_experience"),
            "degree_required": data.get("degree_required"),
            "status": data.get("status", "open")
        }

        job_id = insert_job(job_doc)
        return jsonify({"status": "success", "job_id": job_id}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===========================
# Improve Resume Suggestions
# ===========================
@app.route("/improve", methods=["GET"])
def improve_resume():
    try:
        resume_hash = request.args.get("resume_hash")
        jd_hash = request.args.get("jd_hash")

        if not resume_hash:
            return jsonify({"status": "error", "message": "resume_hash is required"}), 400

        resume_doc = get_resume_by_hash(resume_hash)
        if not resume_doc:
            return jsonify({"status": "error", "message": "Resume not found"}), 404

        # Backfill jd_hash from most recent history entry for this resume
        if not jd_hash:
            history = get_scoring_history(limit=1, resume_hash=resume_hash)
            if isinstance(history, list) and history:
                first = history[0]
                if isinstance(first, dict) and first.get("jd_hash"):
                    jd_hash = first["jd_hash"]

        jd_doc = None
        if jd_hash:
            jd_doc = get_jobdesc_by_hash(jd_hash)

        suggestions = {
            "resume_hash": resume_hash,
            "jd_hash": jd_hash,
            "missing_jd_skills": [],
            "missing_keywords": [],
            "missing_keywords_from_jd_text": [],
            "jd_extra_keywords": [],
            "experience_gap": None,
            "degree_gap": None,
            "format_suggestions": [],
            "resume_enhancement_tips": [],
            "grammar_issues": []
        }

        resume_skills_norm = normalize_list(resume_doc.get("skills", []))
        resume_text = (resume_doc.get("raw_text") or "")
        resume_tokens = set(tokenize(resume_text))

        if jd_doc:
            # ----- JD-based logic -----
            jd_parsed = jd_doc.get("parsed_json", {}) or {}
            jd_must_skills = normalize_list(jd_parsed.get("must_have_skills", []))
            missing_skills = sorted([s for s in jd_must_skills if s not in resume_skills_norm])
            suggestions["missing_jd_skills"] = missing_skills

            jd_degrees = jd_parsed.get("degrees_required")
            if isinstance(jd_degrees, list) and jd_degrees:
                resume_deg = (resume_doc.get("education") or "").strip()
                if not any(k.lower() in resume_deg.lower() for k in [d.lower() for d in jd_degrees]):
                    suggestions["degree_gap"] = f"Required: {', '.join(jd_degrees)}, Found: {resume_deg or 'Unknown'}"

            jd_exp = jd_parsed.get("experience_required")
            resume_exp = resume_doc.get("experience_years", 0)
            if isinstance(jd_exp, int) and resume_exp < jd_exp:
                suggestions["experience_gap"] = f"Required: {jd_exp} years, Found: {resume_exp} years"

            jd_text = (jd_doc.get("jd_text") or "")
            jd_top = top_keywords(jd_text, topk=30)
            jd_extras = [k for k in jd_top if k not in jd_must_skills]
            suggestions["jd_extra_keywords"] = jd_extras[:15]

            missing_kw = [k for k in jd_top if k not in resume_tokens and k not in resume_skills_norm]
            noise = {"responsibilities", "requirements", "role", "team", "work", "good", "strong", "using", "skills"}
            suggestions["missing_keywords_from_jd_text"] = [k for k in missing_kw if k not in noise and len(k) > 2][:15]
            suggestions["missing_keywords"] = suggestions["missing_keywords_from_jd_text"]
        else:
            # ----- Fallback logic (no JD available) -----
            common_keywords = [
                "python", "java", "c++", "javascript", "sql", "git",
                "apis", "machine learning", "data analysis", "cloud",
                "aws", "azure", "docker", "kubernetes", "linux",
                "agile", "scrum", "debugging", "problem solving"
            ]
            missing_kw = [
                kw for kw in common_keywords
                if kw.lower() not in resume_tokens and kw.lower() not in resume_skills_norm
            ]
            suggestions["missing_keywords"] = missing_kw[:15]  # Limit to top 15

        # ---- Formatting Suggestions ----
        raw_lower = resume_text.lower()
        if "summary" not in raw_lower:
            suggestions["format_suggestions"].append(
                "Add a Professional Summary showcasing your core skills and achievements at the top."
            )
        if "experience" not in raw_lower:
            suggestions["format_suggestions"].append(
                "Add a Work Experience section with relevant details."
            )
        if "education" not in raw_lower:
            suggestions["format_suggestions"].append(
                "Ensure an Education section is present."
            )
        if len(resume_doc.get("skills", [])) < 8:
            suggestions["format_suggestions"].append(
                "Expand the Skills section with more targeted keywords."
            )

        # ---- Tips ----
        tips = []
        if not re.search(r"\b(achiev|impact|improv|reduc|increas|optimi|led|delivered|launched)\b", raw_lower):
            tips.append("Add measurable impact using numbers or percentages.")
        if not re.search(r"\b(built|developed|designed|implemented|automated|deployed|analyzed|visualized|optimized)\b", raw_lower):
            tips.append("Start bullets with strong action verbs.")
        if "project" not in raw_lower and "projects" not in raw_lower:
            tips.append("Include 1–2 project highlights to demonstrate applied skills.")
        if jd_doc and suggestions["missing_jd_skills"]:
            tips.append("Weave missing JD skills into relevant bullets.")
        tips.append("Mirror JD terminology in your resume wording.")
        suggestions["resume_enhancement_tips"] = tips

        # ---------- GRAMMAR AND STRUCTURE CHECKS ----------
        import re as _re

        def _split_sentences(text: str):
            return [s.strip() for s in _re.split(r'(?<=[\.\!\?])\s+', text) if s.strip()]

        def _tokenize_words(text: str):
            return _re.findall(r"[A-Za-z][A-Za-z\-']+", text)

        def _extract_bullets(text: str):
            lines = [ln.strip() for ln in text.splitlines()]
            bullets = []
            for ln in lines:
                if _re.match(r'^(\-|\u2022|\*|\d+\.)\s+', ln):
                    bullets.append(ln)
            return bullets

        def _detect_repeated_words(text: str):
            issues = []
            pattern = _re.compile(r"\b(\w+)\s+\1\b", flags=_re.IGNORECASE)
            for m in pattern.finditer(text):
                w = m.group(1)
                issues.append(f"Repeated word detected: “{w} {w}”.")
            return issues

        def _detect_long_sentences(text: str, max_words: int = 30):
            issues = []
            for s in _split_sentences(text):
                wc = len(_tokenize_words(s))
                if wc > max_words:
                    issues.append(f"Long sentence ({wc} words) — consider splitting: “{s[:120]}...”")
            return issues

        def _detect_sentence_capitalization(text: str):
            issues = []
            for s in _split_sentences(text):
                if s and s[0].isalpha() and not s.isupper():
                    issues.append(f"Sentence should start with a capital letter: “{s[:80]}...”")
            return issues

        def _detect_long_bullets(text: str, max_words: int = 30):
            issues = []
            bullets = _extract_bullets(text)
            for b in bullets:
                wc = len(_tokenize_words(b))
                if wc > max_words:
                    issues.append(f"Bullet too long ({wc} words) — try splitting or tightening: “{b[:120]}...”")
            return issues

        def _detect_passive_voice_hints(text: str):
            issues = []
            pattern = _re.compile(r'\b(was|were|is|are|been|being)\s+\w+(ed|en)\b', flags=_re.IGNORECASE)
            for m in pattern.finditer(text):
                frag = text[m.start(): m.end()+40]
                issues.append(f"Possible passive voice — consider active phrasing: “{frag.strip()[:120]}...”")
            return issues

        def _detect_inconsistent_punctuation(text: str):
            bullets = _extract_bullets(text)
            if not bullets:
                return []
            endings = [b.strip().endswith('.') for b in bullets if len(_tokenize_words(b)) > 4]
            if not endings:
                return []
            if any(endings) and not all(endings):
                return ["Inconsistent punctuation at bullet ends — standardize (either all end with '.' or none)."]
            return []

        grammar_issues = []
        grammar_issues += _detect_repeated_words(resume_text)
        grammar_issues += _detect_long_sentences(resume_text, max_words=30)
        grammar_issues += _detect_sentence_capitalization(resume_text)
        grammar_issues += _detect_long_bullets(resume_text, max_words=30)
        grammar_issues += _detect_passive_voice_hints(resume_text)
        grammar_issues += _detect_inconsistent_punctuation(resume_text)
        suggestions["grammar_issues"] = grammar_issues[:25]

        return jsonify(suggestions), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===========================
# Health & Root routes
# ===========================
@app.route("/", methods=["GET"])
def root():
    return {"status": "ok"}, 200


@app.route("/health", methods=["GET"])
def health():
    return {"status": "healthy"}, 200


@app.route("/reports/kpis", methods=["GET"])
def reports_kpis():
    try:
        import datetime

        # For backward compatibility; we'll compute last7 again with tz-aware below
        now = datetime.datetime.utcnow()
        _ = now - datetime.timedelta(days=7)

        # 1) Total resumes processed (distinct in scoring history)
        history_all = get_scoring_history(limit=10000)  # adjust up/down as needed
        total_resumes = len({h.get("resume_hash") for h in history_all if h.get("resume_hash")})

        # 2) Total JDs uploaded (inferred from unique jd_hashes in history)
        jd_hashes = {h.get("jd_hash") for h in history_all if h.get("jd_hash")}
        total_jds = len(jd_hashes)

        # 3) Average overall score (from score_json.overall)
        scores_vals = []
        for h in history_all:
            v = (h.get("score_json") or {}).get("overall")
            if isinstance(v, (int, float)):
                scores_vals.append(float(v))
        avg_overall = round((sum(scores_vals) / len(scores_vals)) if scores_vals else 0, 1)

        # 4) Runs in last 7 days (tz-aware comparison)
        recent_runs_7d = 0
        from datetime import datetime as dt, timezone, timedelta
        last7 = dt.now(timezone.utc) - timedelta(days=7)

        def _to_dt(ts):
            if hasattr(ts, "isoformat"):
                return ts if getattr(ts, "tzinfo", None) else ts.replace(tzinfo=timezone.utc)
            if isinstance(ts, str):
                s = ts.strip()
                try:
                    return dt.strptime(s, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
                except Exception:
                    pass
                try:
                    return dt.fromisoformat(s.replace("Z", "+00:00"))
                except Exception:
                    return None
            return None

        for h in history_all:
            ts = _to_dt(h.get("created_at") or h.get("timestamp"))
            if ts and ts >= last7:
                recent_runs_7d += 1

        return jsonify({
            "total_resumes": total_resumes,
            "total_jds": total_jds,
            "avg_overall": avg_overall,
            "recent_runs_7d": recent_runs_7d
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/reports/recent_scores", methods=["GET"])
def reports_recent_scores():
    try:
        # Reuse your existing history helper; fetch last 10 by timestamp desc
        items = get_scoring_history(limit=10)
        from datetime import datetime as dt

        def _to_dt(ts):
            if hasattr(ts, "isoformat"):
                return ts
            if isinstance(ts, str):
                s = ts.strip()
                try:
                    return dt.strptime(s, "%a, %d %b %Y %H:%M:%S %Z")
                except Exception:
                    pass
                try:
                    return dt.fromisoformat(s.replace("Z", "+00:00"))
                except Exception:
                    pass
                for fmt in (
                    "%Y-%m-%d %H:%M:%S",
                    "%Y/%m/%d %H:%M:%S",
                    "%Y-%m-%d %H:%M",
                    "%Y/%m/%d %H:%M",
                    "%d-%m-%Y %H:%M:%S",
                    "%d-%m-%Y %H:%M",
                ):
                    try:
                        return dt.strptime(s, fmt)
                    except Exception:
                        continue
            return None

        def _pluck_overall(h):
            sj = h.get("score_json") or {}
            v = sj.get("overall")
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str):
                try:
                    return float(v)
                except Exception:
                    return None
            return None

        rows = []
        for h in items:
            ts = _to_dt(h.get("created_at"))
            if ts is None:
                ts = _to_dt(h.get("timestamp") or h.get("createdAt") or h.get("ts"))
            if ts is None:
                continue

            s_val = _pluck_overall(h)
            if s_val is None:
                continue

            rows.append({"timestamp": ts.isoformat(), "overall_score": s_val})

        rows = sorted(rows, key=lambda x: x["timestamp"])[-10:]
        return jsonify({"recent_scores": rows}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/reports/recent_runs", methods=["GET"])
def reports_recent_runs():
    try:
        limit = int(request.args.get("limit", 10))
        items = get_scoring_history(limit=limit)

        def _safe_str(x):
            return x if isinstance(x, str) else (str(x) if x is not None else "")

        def _pluck_overall(h):
            sj = h.get("score_json") or {}
            v = sj.get("overall")
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str):
                try:
                    return float(v)
                except Exception:
                    return None
            return None

        rows = []
        for h in items:
            rows.append({
                "created_at": _safe_str(h.get("created_at") or h.get("timestamp") or ""),
                "resume_hash": _safe_str(h.get("resume_hash")),
                "jd_hash": _safe_str(h.get("jd_hash")),
                "job_role": _safe_str(h.get("job_role")),
                "overall_score": _pluck_overall(h),
            })

        return jsonify({"recent_runs": rows}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/reports/avg_categories", methods=["GET"])
def reports_avg_categories():
    try:
        items = get_scoring_history(limit=10000)

        sums = {
            "skills": 0.0,
            "experience": 0.0,
            "education": 0.0,
            "formatting": 0.0,
            "keywords": 0.0
        }
        count = 0

        for h in items:
            sj = h.get("score_json") or {}
            has_any = False
            for k in list(sums.keys()):
                v = sj.get(k)
                if isinstance(v, (int, float)):
                    sums[k] += float(v)
                    has_any = True
            if has_any:
                count += 1

        avgs = {k: (sums[k] / count if count else 0.0) for k in sums}

        return jsonify({"avg_categories": avgs, "count": count}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/reports/top_missing_jd_skills", methods=["GET"])
def reports_top_missing_jd_skills():
    try:
        # How many recent runs to analyze (default 500 to keep it efficient)
        limit = int(request.args.get("limit", 500))
        items = get_scoring_history(limit=limit)

        from collections import Counter

        def _norm_list(ls):
            return sorted({(s or "").strip().lower() for s in (ls or []) if isinstance(s, str) and s.strip()})

        counter = Counter()

        for h in items:
            resume_hash = h.get("resume_hash")
            jd_hash = h.get("jd_hash")
            if not resume_hash or not jd_hash:
                continue

            # Fetch resume and JD docs
            resume_doc = get_resume_by_hash(resume_hash) or {}
            jd_doc = get_jobdesc_by_hash(jd_hash) or {}

            resume_skills = _norm_list(resume_doc.get("skills", []))
            jd_parsed = jd_doc.get("parsed_json", {}) or {}
            jd_must = _norm_list(jd_parsed.get("must_have_skills", []))

            if not jd_must:
                continue

            missing = [s for s in jd_must if s not in resume_skills]
            # Count each missing skill once per run (not by frequency within text)
            for s in missing:
                counter[s] += 1

        # Top N skills
        top = int(request.args.get("top", 10))
        top_missing = counter.most_common(top)

        # Return as [{"skill": ..., "count": ...}, ...]
        result = [{"skill": s, "count": c} for s, c in top_missing]

        return jsonify({"top_missing_jd_skills": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===========================
# History (paginated)
# ===========================
from database.db_operations import scores  # ensure collection is available

@app.route("/history", methods=["GET"])
def history():
    try:
        limit = max(1, min(int(request.args.get("limit", 20)), 1000))
        offset = max(0, int(request.args.get("offset", 0)))

        resume_hash = request.args.get("resume_hash")
        jd_hash = request.args.get("jd_hash")

        query = {}
        if resume_hash:
            query["resume_hash"] = resume_hash
        if jd_hash:
            query["jd_hash"] = jd_hash

        total = scores.count_documents(query)
        cursor = (
            scores.find(query)
                  .sort("created_at", -1)
                  .skip(offset)
                  .limit(limit)
        )

        items = []
        for doc in cursor:
            d = dict(doc)
            d["_id"] = str(d.get("_id"))
            items.append(d)

        return jsonify({"items": items, "total": total, "limit": limit, "offset": offset}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    # In production, set debug via env var; left True for development
    app.run(debug=True, host="0.0.0.0", port=5000)
