import os
import re
import hashlib
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    send_from_directory,
    url_for,
    session,
    redirect
)
from werkzeug.utils import secure_filename
from pypdf import PdfReader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.secret_key = "RESUMind_AI_SECRET_KEY_2026"

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Login details
USER_USERNAME = "user"
USER_PASSWORD = "user123"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# In-memory admin statistics
stats = {
    "total_scans": 0,
    "feedbacks": []
}


# =========================================================
# HELPERS
# =========================================================

def extract_text_from_pdf(file_path):
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + " "
    except Exception as e:
        print(f"Extraction Error: {e}")
    return text.strip()


def safe_render_template(template_name, **context):
    template_path = os.path.join(app.template_folder, template_name)
    if not os.path.exists(template_path):
        return (
            f"<h3>Error: Template '{template_name}' not found "
            f"in '{app.template_folder}'.</h3>",
            404
        )
    return render_template(template_name, **context)


def login_required():
    return session.get("logged_in") is True


def admin_required():
    return (
        session.get("logged_in") is True
        and session.get("role") == "admin"
    )



# =========================================================
# USER SIGNUP DATABASE
# =========================================================

DATABASE = os.path.join(BASE_DIR, "users.db")


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_user_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# =========================================================
# LOGIN / LOGOUT
# =========================================================

@app.route("/user-login", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Keep the original demo login working.
        if username == USER_USERNAME and password == USER_PASSWORD:
            session.clear()
            session["logged_in"] = True
            session["role"] = "user"
            session["username"] = username
            return redirect(url_for("index"))

        # Check registered signup users.
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE name = ?",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["logged_in"] = True
            session["role"] = "user"
            session["username"] = user["name"]
            session["email"] = user["email"]
            return redirect(url_for("index"))

        return render_template(
            "user_login.html",
            error="Invalid username or password."
        )

    return render_template("user_login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not password:
            return render_template(
                "signup.html",
                error="All fields are required."
            )

        if len(password) < 6:
            return render_template(
                "signup.html",
                error="Password must contain at least 6 characters."
            )

        conn = get_db()

        existing = conn.execute(
            "SELECT id FROM users WHERE name = ? OR email = ?",
            (name, email)
        ).fetchone()

        if existing:
            conn.close()
            return render_template(
                "signup.html",
                error="Username or email already exists."
            )

        hashed_password = generate_password_hash(password)

        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, hashed_password)
        )
        conn.commit()
        conn.close()

        # After signup, go to the existing login page.
        # The original RESUMind interface is not changed.
        return redirect(url_for("user_login"))

    return render_template("signup.html")


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.clear()
            session["logged_in"] = True
            session["role"] = "admin"
            session["username"] = username
            return redirect(url_for("admin"))

        return render_template(
            "admin_login.html",
            error="Invalid admin username or password."
        )

    return render_template("admin_login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("user_login"))


# =========================================================
# PAGE ROUTES
# =========================================================

@app.route("/")
def index():
    if not login_required():
        return redirect(url_for("user_login"))
    return safe_render_template("index.html")


@app.route("/scorer")
def scorer():
    if not login_required():
        return redirect(url_for("user_login"))
    return safe_render_template("scorer.html")


@app.route("/skill-gap")
def skill_gap():
    if not login_required():
        return redirect(url_for("user_login"))
    return safe_render_template("skill_gap.html")


@app.route("/analyser")
def analyser():
    if not login_required():
        return redirect(url_for("user_login"))
    return safe_render_template("analyser.html")


@app.route("/all-jobs")
def all_jobs():
    if not login_required():
        return redirect(url_for("user_login"))
    return safe_render_template("all_jobs.html")


@app.route("/admin")
def admin():
    if not admin_required():
        return redirect(url_for("admin_login"))
    return safe_render_template("admin.html", stats=stats, companies=company_profiles)


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    if not login_required():
        return redirect(url_for("user_login"))
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/view_resume/<filename>")
def view_resume(filename):
    if not login_required():
        return redirect(url_for("user_login"))

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    if not os.path.exists(file_path):
        return "Resume not found", 404

    text = extract_text_from_pdf(file_path)
    words = text.lower().split()

    skills = [
        "python", "java", "sql", "html",
        "css", "react", "aws", "docker"
    ]

    matched = [
        s for s in skills
        if re.search(r"\b" + re.escape(s) + r"\b", text.lower())
    ]

    data = {
        "filename": filename,
        "score": min(100, max(10, len(words) // 5)),
        "compatibility": (
            "Good Match" if len(matched) >= 3
            else "Needs Improvement"
        ),
        "word_count": len(words),
        "skills": matched
    }

    return safe_render_template("resume_view.html", data=data)


# =========================================================
# ATS SCORE
# =========================================================

@app.route("/get_score", methods=["POST"])
def get_score():
    if not login_required():
        return jsonify({
            "status": "error",
            "message": "Please login first."
        }), 401

    if "resume" not in request.files:
        return jsonify({
            "status": "error",
            "message": "No resume file uploaded"
        }), 400

    file = request.files["resume"]

    if file.filename == "":
        return jsonify({
            "status": "error",
            "message": "No file selected"
        }), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )
    file.save(file_path)

    stats["total_scans"] += 1

    raw_text = extract_text_from_pdf(file_path)
    text = raw_text.lower()
    words = text.split()
    word_count = len(words)

    if word_count < 20:
        return jsonify({
            "status": "error",
            "message": (
                "Failed to read text from PDF. "
                "Please upload a readable text-based PDF."
            )
        }), 400

    file_hash = int(
        hashlib.md5(text.encode("utf-8")).hexdigest(),
        16
    )

    skill_patterns = {
        "python": r"\bpython\b",
        "java": r"\bjava\b",
        "c++": r"\bc\+\+\b",
        "javascript": r"\bjavascript\b",
        "typescript": r"\btypescript\b",
        "html": r"\bhtml\b",
        "css": r"\bcss\b",
        "react": r"\breact\b",
        "angular": r"\bangular\b",
        "vue": r"\bvue\b",
        "node": r"\bnode\b",
        "express": r"\bexpress\b",
        "django": r"\bdjango\b",
        "flask": r"\bflask\b",
        "fastapi": r"\bfastapi\b",
        "sql": r"\bsql\b",
        "mysql": r"\bmysql\b",
        "postgresql": r"\bpostgresql\b",
        "mongodb": r"\bmongodb\b",
        "aws": r"\baws\b",
        "azure": r"\bazure\b",
        "docker": r"\bdocker\b",
        "kubernetes": r"\bkubernetes\b",
        "git": r"\bgit\b",
        "linux": r"\blinux\b",
        "pandas": r"\bpandas\b",
        "numpy": r"\bnumpy\b",
        "excel": r"\bexcel\b",
        "machine learning": r"\bmachine learning\b",
        "data analysis": r"\bdata analysis\b",
        "rest api": r"\brest\s*api\b",
        "devops": r"\bdevops\b",
        "agile": r"\bagile\b"
    }

    found_skills = [
        skill for skill, pattern in skill_patterns.items()
        if re.search(pattern, text)
    ]

    skill_score = min(35.0, len(found_skills) * 2.5)

    sections = {
        "summary": [
            "summary", "profile", "objective", "about me"
        ],
        "education": [
            "education", "academic", "qualifications", "degree"
        ],
        "experience": [
            "experience", "employment", "work history", "internship"
        ],
        "skills": [
            "skills", "technical skills", "competencies"
        ],
        "projects": [
            "projects", "personal projects", "portfolio"
        ],
        "certifications": [
            "certifications", "certificates", "licenses"
        ]
    }

    detected_sections = [
        sec for sec, kws in sections.items()
        if any(kw in text for kw in kws)
    ]

    section_score = min(
        20.0,
        len(detected_sections) * 3.33
    )

    experience_score = 0.0

    if "experience" in detected_sections:
        experience_score += 4.0

    if "internship" in text:
        experience_score += 3.0

    years = re.findall(r"\b(?:19|20)\d{2}\b", text)

    experience_score += min(
        5.0,
        len(set(years)) * 1.25
    )

    role_titles = [
        "developer",
        "engineer",
        "analyst",
        "manager",
        "intern",
        "architect",
        "lead"
    ]

    found_roles = sum(
        1 for role in role_titles
        if role in text
    )

    experience_score = min(
        15.0,
        experience_score + min(3.0, found_roles * 1.0)
    )

    project_score = 0.0

    if "projects" in detected_sections:
        project_score += 5.0

    action_verbs = [
        "developed", "built", "created",
        "implemented", "designed",
        "architected", "deployed",
        "optimized", "managed", "scaled"
    ]

    verb_count = sum(
        1 for verb in action_verbs
        if verb in text
    )

    project_score = min(
        15.0,
        project_score + min(10.0, verb_count * 1.5)
    )

    education_score = 0.0

    if "education" in detected_sections:
        education_score += 4.0

    edu_keywords = [
        "degree", "b.tech", "btech",
        "mca", "b.sc", "m.sc",
        "bachelor", "master", "phd",
        "university", "college"
    ]

    edu_matches = sum(
        1 for word in edu_keywords
        if word in text
    )

    education_score = min(
        10.0,
        education_score + min(6.0, edu_matches * 1.5)
    )

    if 250 <= word_count <= 700:
        length_score = 5.0
    elif 150 <= word_count < 250 or 700 < word_count <= 1000:
        length_score = 3.5
    else:
        length_score = 1.5

    hash_variance = (
        (file_hash % 40) - 20
    ) / 10.0

    raw_total = (
        skill_score
        + section_score
        + experience_score
        + project_score
        + education_score
        + length_score
        + hash_variance
    )

    overall_score = max(
        5,
        min(100, round(raw_total))
    )

    if overall_score >= 80:
        level = "Excellent ATS Compatibility"
    elif overall_score >= 65:
        level = "Good ATS Compatibility"
    elif overall_score >= 45:
        level = "Medium ATS Match"
    else:
        level = "Low Compatibility - Needs Improvement"

    ats_checks = [
        {
            "name": "Word Count & Length",
            "detail": f"Extracted {word_count} words.",
            "status": (
                "passed"
                if 250 <= word_count <= 700
                else "warning"
            )
        },
        {
            "name": "Technical Keyword Match",
            "detail": (
                f"Detected {len(found_skills)} tech skills."
            ),
            "status": (
                "passed"
                if len(found_skills) >= 5
                else "warning"
            )
        },
        {
            "name": "Essential Resume Sections",
            "detail": (
                f"Found {len(detected_sections)} section headers."
            ),
            "status": (
                "passed"
                if len(detected_sections) >= 4
                else "warning"
            )
        },
        {
            "name": "Action Verbs & Impact",
            "detail": (
                f"Detected {verb_count} action verbs."
            ),
            "status": (
                "passed"
                if verb_count >= 3
                else "warning"
            )
        }
    ]

    return jsonify({
        "status": "success",
        "file_name": filename,
        "direct_link": url_for(
            "uploaded_file",
            filename=filename
        ),
        "overall_score": overall_score,
        "compatibility_level": level,
        "word_count": word_count,
        "detected_skills": found_skills,
        "detected_sections": detected_sections,
        "ats_checks": ats_checks
    })


# =========================================================
# SKILL GAP
# =========================================================

@app.route("/get_skill_gap", methods=["POST"])
def get_skill_gap():
    if not login_required():
        return jsonify({
            "status": "error",
            "message": "Please login first."
        }), 401

    if "resume" not in request.files:
        return jsonify({
            "status": "error",
            "message": "No resume file uploaded"
        }), 400

    file = request.files["resume"]
    filename = secure_filename(file.filename)

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    file.save(file_path)

    raw_text = extract_text_from_pdf(file_path)
    text = raw_text.lower()

    standard_skills = [
        "python", "java", "sql",
        "html", "css", "javascript",
        "react", "aws", "docker",
        "git", "linux", "rest api"
    ]

    found = [
        s for s in standard_skills
        if re.search(
            r"\b" + re.escape(s) + r"\b",
            text
        )
    ]

    missing = [
        s for s in standard_skills
        if s not in found
    ]

    suggestions = []

    if "projects" not in text:
        suggestions.append(
            "Add a detailed 'Projects' section highlighting action verbs."
        )

    if "certifications" not in text:
        suggestions.append(
            "Consider listing relevant technical certifications."
        )

    if len(found) < 5:
        suggestions.append(
            "Include more technical keywords and domain tools."
        )

    if len(text.split()) < 250:
        suggestions.append(
            "Expand on your job responsibilities and measurable outcomes."
        )

    return jsonify({
        "status": "success",
        "missing_skills": missing,
        "suggestions": (
            suggestions
            if suggestions
            else [
                "Your resume structure and key skills look comprehensive!"
            ]
        )
    })


# =========================================================
# COMPANY RECOMMENDATIONS
# =========================================================

# Companies are matched against the same technical skills used by the
# resume analyser. The list is intentionally data-driven so it can be
# expanded later without changing the matching logic.
company_profiles = {
    "TCS": {
        "roles": ["Software Developer", "Full Stack Developer", "Data Analyst", "Cloud Engineer"],
        "skills": ["python", "java", "sql", "javascript", "react", "aws", "azure", "docker", "git"]
    },
    "Infosys": {
        "roles": ["Software Developer", "Java Developer", "Data Analyst", "Cloud Engineer"],
        "skills": ["java", "python", "sql", "javascript", "react", "aws", "azure", "git"]
    },
    "Wipro": {
        "roles": ["Software Developer", "Python Developer", "Cloud Engineer", "DevOps Engineer"],
        "skills": ["python", "java", "sql", "aws", "azure", "docker", "kubernetes", "git"]
    },
    "Accenture": {
        "roles": ["Full Stack Developer", "Software Developer", "Cloud Engineer", "Data Analyst"],
        "skills": ["python", "java", "javascript", "typescript", "react", "sql", "aws", "azure", "docker", "git"]
    },
    "Cognizant": {
        "roles": ["Software Developer", "Full Stack Developer", "Data Analyst", "QA / Automation Tester"],
        "skills": ["java", "python", "javascript", "react", "sql", "testing", "selenium", "git"]
    },
    "HCLTech": {
        "roles": ["Software Developer", "Cloud Engineer", "DevOps Engineer", "QA / Automation Tester"],
        "skills": ["java", "python", "sql", "aws", "azure", "docker", "kubernetes", "testing", "git"]
    },
    "Tech Mahindra": {
        "roles": ["Software Developer", "Full Stack Developer", "DevOps Engineer"],
        "skills": ["java", "python", "javascript", "react", "node", "sql", "docker", "kubernetes", "git"]
    },
    "Capgemini": {
        "roles": ["Full Stack Developer", "Software Developer", "Cloud Engineer", "Data Analyst"],
        "skills": ["java", "python", "javascript", "react", "sql", "aws", "azure", "docker", "git"]
    },
    "Deloitte": {
        "roles": ["Data Analyst", "Software Developer", "Cloud Engineer", "Cybersecurity Analyst"],
        "skills": ["python", "sql", "excel", "data analysis", "aws", "azure", "linux", "cybersecurity", "git"]
    },
    "IBM": {
        "roles": ["Software Developer", "Cloud Engineer", "Data Scientist", "Cybersecurity Analyst"],
        "skills": ["python", "java", "sql", "machine learning", "aws", "docker", "kubernetes", "linux", "git"]
    },
    "Amazon": {
        "roles": ["Software Developer", "Cloud Engineer", "Data Scientist", "DevOps Engineer"],
        "skills": ["python", "java", "sql", "aws", "docker", "kubernetes", "linux", "machine learning", "git"]
    },
    "Microsoft": {
        "roles": ["Software Developer", "Cloud Engineer", "Data Scientist", "DevOps Engineer"],
        "skills": ["python", "java", "javascript", "typescript", "sql", "azure", "docker", "kubernetes", "machine learning", "git"]
    },
    "Oracle": {
        "roles": ["Java Developer", "Database Administrator", "Cloud Engineer", "Software Developer"],
        "skills": ["java", "sql", "oracle", "mysql", "postgresql", "aws", "azure", "linux", "git"]
    },
    "Salesforce": {
        "roles": ["Software Developer", "Full Stack Developer", "Data Analyst"],
        "skills": ["javascript", "typescript", "html", "css", "sql", "python", "react", "git"]
    }
}


def get_company_recommendations(resume_text, job_results=None, limit=8):
    """Return companies ranked by overlap with the uploaded resume skills."""
    text = resume_text.lower()
    resume_skills = set()

    # Reuse the application's known skill vocabulary and detect only
    # skills that actually occur in the resume.
    all_company_skills = sorted({
        skill
        for profile in company_profiles.values()
        for skill in profile["skills"]
    }, key=len, reverse=True)

    for skill in all_company_skills:
        pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
        if re.search(pattern, text):
            resume_skills.add(skill)

    role_by_company = {}
    if job_results:
        for result in job_results:
            role_by_company[result["job"]] = result["match_percentage"]

    recommendations = []
    for company, profile in company_profiles.items():
        matched = [skill for skill in profile["skills"] if skill in resume_skills]
        match_percentage = round((len(matched) / len(profile["skills"])) * 100)

        # Small role relevance bonus when the resume also matches one of
        # the job roles returned by the analyser.
        role_matches = [
            role_by_company[role]
            for role in profile["roles"]
            if role in role_by_company
        ]
        if role_matches:
            match_percentage = min(100, round(match_percentage * 0.75 + max(role_matches) * 0.25))

        if matched:
            recommendations.append({
                "company": company,
                "match": f"{match_percentage}%",
                "match_percentage": match_percentage,
                "matched_skills": matched,
                "roles": profile["roles"]
            })

    recommendations.sort(
        key=lambda item: (item["match_percentage"], len(item["matched_skills"])),
        reverse=True
    )

    return recommendations[:limit]



@app.route("/company-approach")
def company_approach():
    if not login_required():
        return redirect(url_for("user_login"))
    return safe_render_template("company_approach.html", companies=company_profiles)

@app.route("/companies")
def companies():
    if not login_required():
        return redirect(url_for("user_login"))

    return jsonify({
        "status": "success",
        "companies": [
            {"company": name, "roles": profile["roles"], "skills": profile["skills"]}
            for name, profile in company_profiles.items()
        ]
    })


# =========================================================
# RESUME-BASED JOB ANALYSER
# =========================================================

@app.route("/analyze", methods=["POST"])
def analyze():
    if not login_required():
        return jsonify({
            "status": "error",
            "message": "Please login first."
        }), 401

    if "resume" not in request.files:
        return jsonify({
            "status": "error",
            "message": "No resume file uploaded"
        }), 400

    file = request.files["resume"]

    if file.filename == "":
        return jsonify({
            "status": "error",
            "message": "No file selected"
        }), 400

    filename = secure_filename(file.filename)

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    file.save(file_path)

    text = extract_text_from_pdf(file_path).lower()

    # Computer-related job library.
    # Only roles that match the uploaded resume are returned.
    job_profiles = {
        "Frontend Developer": [
            "html", "css", "javascript",
            "react", "angular", "vue", "typescript"
        ],

        "Backend Developer": [
            "python", "java", "node",
            "express", "django", "flask",
            "sql", "rest api"
        ],

        "Full Stack Developer": [
            "html", "css", "javascript",
            "react", "python", "node", "sql"
        ],

        "Software Developer": [
            "python", "java", "c++",
            "javascript", "git", "sql"
        ],

        "Python Developer": [
            "python", "django", "flask",
            "fastapi", "sql", "git"
        ],

        "Java Developer": [
            "java", "spring", "sql",
            "hibernate", "git", "rest api"
        ],

        "Data Analyst": [
            "python", "sql", "excel",
            "pandas", "numpy", "data analysis"
        ],

        "Data Scientist": [
            "python", "pandas", "numpy",
            "machine learning", "sql", "excel"
        ],

        "Machine Learning Engineer": [
            "python", "numpy", "pandas",
            "machine learning", "tensorflow",
            "pytorch", "git"
        ],

        "Cloud Engineer": [
            "aws", "azure", "linux",
            "docker", "kubernetes", "git"
        ],

        "Cybersecurity Analyst": [
            "linux", "networking", "python",
            "cybersecurity", "security", "git"
        ],

        "Mobile App Developer": [
            "java", "kotlin", "android",
            "flutter", "dart", "firebase"
        ],

        "Database Administrator": [
            "sql", "mysql", "postgresql",
            "oracle", "mongodb", "linux"
        ],

        "QA / Automation Tester": [
            "testing", "selenium",
            "python", "java", "javascript",
            "automation", "sql"
        ],

        "DevOps Engineer": [
            "linux", "git", "docker",
            "kubernetes", "aws", "azure",
            "devops", "jenkins"
        ]
    }

    results = []
    resume_skills = set()

    for job, skills in job_profiles.items():

        matched = []

        for skill in skills:
            pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"

            if re.search(pattern, text):
                matched.append(skill)
                resume_skills.add(skill)

        match_pct = (
            round((len(matched) / len(skills)) * 100)
            if skills else 0
        )

        # Only show roles that have meaningful resume matching.
        if match_pct >= 20:
            results.append({
                "job": job,
                "match": f"{match_pct}%",
                "match_percentage": match_pct,
                "matched_skills": matched,
                "total_required_skills": len(skills)
            })

    # Highest match first.
    results.sort(
        key=lambda item: item["match_percentage"],
        reverse=True
    )

    company_recommendations = get_company_recommendations(
        text,
        job_results=results,
        limit=8
    )

    return jsonify({
        "status": "success",
        "jobs": results,
        "companies": company_recommendations,
        "resume_skills": sorted(resume_skills),
        "message": (
            "Matching jobs found based on your resume."
            if results
            else
            "No strong computer-job matches were found. "
            "Add more technical skills to your resume."
        )
    })


# =========================================================
# FEEDBACK
# =========================================================

@app.route("/feedback", methods=["POST"])
def feedback():
    if not login_required():
        return jsonify({
            "status": "error",
            "message": "Please login first."
        }), 401

    data = request.get_json(silent=True)

    if (
        data
        and "message" in data
        and isinstance(data["message"], str)
        and data["message"].strip()
    ):
        stats["feedbacks"].append(
            data["message"].strip()
        )

        return jsonify({
            "status": "success"
        })

    return jsonify({
        "status": "error",
        "message": "Invalid feedback"
    }), 400


# =========================================================
# NO-CACHE AFTER REQUEST
# =========================================================

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, max-age=0"
    )
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    create_user_table()
    app.run(
        debug=True,
        port=5000
    )
