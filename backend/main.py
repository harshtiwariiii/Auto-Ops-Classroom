from fastapi import FastAPI, File, UploadFile, Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Dict, Any
import uvicorn
import os
import pdfplumber
from docx import Document
import sqlite3
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import spacy
import hashlib
from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseModel
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

# -----------------------------------
# 🔓 ENABLE CORS (Add this block here)
# -----------------------------------
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],       # Allow all origins (change later for production)
#     allow_credentials=True,
#     allow_methods=["*"],       # Allow all HTTP methods
#     allow_headers=["*"],       # Allow all headers
# )
# ============================================================
# BASIC APP + PATHS
# ============================================================
app = FastAPI(title="AutoOps Classroom API")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

def db(path: str):
    return sqlite3.connect(str(DATA_DIR / path), check_same_thread=False)


# ============================================================
# DB INITIALIZATION (SAFE TO RUN ON EVERY START)
# ============================================================
def init_db():
    # ----- users.db -----
    conn_u = db("users.db")
    cur_u = conn_u.cursor()
    cur_u.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL,
            full_name     TEXT
        )
    """)
    conn_u.commit()
    conn_u.close()

    # ----- courses.db -----
    conn_c = db("courses.db")
    cur_c = conn_c.cursor()

    # courses table
    cur_c.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            course_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name    TEXT NOT NULL,
            course_details TEXT
        )
    """)

    # course_skills for recommendation engine
    cur_c.execute("""
        CREATE TABLE IF NOT EXISTS course_skills (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            skill     TEXT NOT NULL,
            weight    REAL NOT NULL,
            FOREIGN KEY(course_id) REFERENCES courses(course_id)
        )
    """)

    # modules (steps inside a course)
    cur_c.execute("""
        CREATE TABLE IF NOT EXISTS modules (
            module_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id   INTEGER NOT NULL,
            title       TEXT NOT NULL,
            description TEXT,
            order_index INTEGER DEFAULT 0,
            FOREIGN KEY(course_id) REFERENCES courses(course_id)
        )
    """)

    # lessons inside modules
    cur_c.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            lesson_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id      INTEGER NOT NULL,
            title          TEXT NOT NULL,
            video_url      TEXT,
            notes          TEXT,
            difficulty     TEXT,
            order_index    INTEGER DEFAULT 0,
            FOREIGN KEY(module_id) REFERENCES modules(module_id)
        )
    """)

    # lesson_progress per student
    cur_c.execute("""
        CREATE TABLE IF NOT EXISTS lesson_progress (
            user_id     INTEGER NOT NULL,
            lesson_id   INTEGER NOT NULL,
            completed   INTEGER NOT NULL DEFAULT 0,
            last_opened TEXT,
            PRIMARY KEY(user_id, lesson_id),
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            FOREIGN KEY(lesson_id) REFERENCES lessons(lesson_id)
        )
    """)

    # lesson_notes per student
    cur_c.execute("""
        CREATE TABLE IF NOT EXISTS lesson_notes (
            user_id    INTEGER NOT NULL,
            lesson_id  INTEGER NOT NULL,
            notes      TEXT,
            updated_at TEXT,
            PRIMARY KEY(user_id, lesson_id),
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            FOREIGN KEY(lesson_id) REFERENCES lessons(lesson_id)
        )
    """)

    conn_c.commit()
    conn_c.close()


init_db()


# ============================================================
# JWT CONFIG & AUTH HELPERS
# ============================================================
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
security = HTTPBearer()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])  # ensure string for JWT "sub"
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        payload["sub"] = str(payload.get("sub"))
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {str(e)}")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = decode_token(credentials.credentials)
    return {
        "user_id": payload["sub"],
        "role": payload.get("role"),
        "username": payload.get("username")
    }


def get_current_user_from_request(request: Request):
    auth = request.headers.get("Authorization") or request.headers.get("authorization")
    if not auth:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization must start with Bearer")

    token = auth.split(" ", 1)[1].strip()
    payload = decode_token(token)

    return {
        "user_id": payload["sub"],
        "role": payload.get("role"),
        "username": payload.get("username")
    }


def require_role(roles: List[str]):
    def checker(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker


# ============================================================
# Pydantic MODELS
# ============================================================
class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    role: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class ProgressUpdate(BaseModel):
    completed: bool


class NoteUpdate(BaseModel):
    notes: str

class CourseUpdate(BaseModel):
    course_name: Optional[str] = None
    course_details: Optional[str] = None


class ModuleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    video_url: Optional[str] = None
    notes: Optional[str] = None
    difficulty: Optional[str] = None
    github_url: Optional[str] = None


# ============================================================
# SKILL EXTRACTION
# ============================================================
SKILL_KEYWORDS = [
    # -------------------------
    # Programming Languages
    # -------------------------
    "python", "java", "c", "c++", "c#", "golang", "go", "javascript", "typescript",
    "ruby", "rust", "swift", "kotlin", "scala", "php", "r", "matlab",
    "shell scripting", "bash", "powershell",

    # -------------------------
    # DevOps / Infra Tools
    # -------------------------
    "docker", "kubernetes", "helm", "terraform", "ansible", "chef", "puppet",
    "jenkins", "gitlab ci", "github actions", "argocd", "fluxcd",
    "prometheus", "grafana", "elastic stack", "elk", "nginx", "apache server",
    "devops", "mlops", "sre", "site reliability engineering",

    # -------------------------
    # Cloud Platforms
    # -------------------------
    "aws", "azure", "gcp", "google cloud", "amazon web services",
    "lambda", "ec2", "s3", "cloudwatch", "cloudformation",
    "kinesis", "bigquery", "databricks", "cloud run", "firebase",

    # -------------------------
    # Data Engineering
    # -------------------------
    "sql", "nosql", "postgresql", "mysql", "mongodb", "redis", "cassandra",
    "snowflake", "data warehouse", "etl", "elt", "airflow", "hadoop",
    "spark", "hive", "kafka", "data engineering",

    # -------------------------
    # Machine Learning / AI
    # -------------------------
    "machine learning", "deep learning", "neural networks",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch",
    "opencv", "transformers", "nlp", "computer vision",
    "llm", "large language models", "rag", "vector databases",
    "huggingface", "model training", "hyperparameter tuning",

    # -------------------------
    # Web Development
    # -------------------------
    "html", "css", "react", "nextjs", "angular", "vue", "nodejs",
    "express", "django", "flask", "fastapi", "rest api", "graphql",
    "websockets", "responsive design", "bootstrap", "tailwind css",

    # -------------------------
    # Cybersecurity
    # -------------------------
    "ethical hacking", "network security", "penetration testing",
    "nmap", "burpsuite", "owasp", "metasploit", "sql injection",
    "firewall", "encryption", "cryptography", "cybersecurity",
    "command line interface", "cli tools",

    # -------------------------
    # Computer Science Fundamentals
    # -------------------------
    "data structures", "algorithms", "operating systems", "dbms",
    "networking", "computer networks", "os", "cn", "system design",
    "oop", "object oriented programming", "distributed systems",

    # -------------------------
    # Tools / Version Control
    # -------------------------
    "git", "github", "gitlab", "jira", "confluence", "postman",
    "swagger", "vim", "visual studio code", "intellij", "pycharm",

    # -------------------------
    # Data Science
    # -------------------------
    "statistics", "probability", "data visualization",
    "matplotlib", "seaborn", "plotly", "feature engineering",
    "data cleaning", "eda", "business intelligence",

    # -------------------------
    # Soft Skills (Optional)
    # -------------------------
    "communication", "teamwork", "leadership", "agile", "scrum", "presentation skills",
]


try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None


def extract_text_from_pdf(path: str) -> str:
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


def extract_text_from_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def extract_name(text: str) -> str:
    if not nlp:
        for line in text.splitlines():
            if 2 < len(line) < 40 and not any(ch.isdigit() for ch in line):
                return line.strip()
        return "Unknown"

    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text
    return "Unknown"


def extract_skills(text: str):
    low = text.lower()
    return [s for s in SKILL_KEYWORDS if s in low]


# ============================================================
# ROOT HEALTH CHECK
# ============================================================
@app.get("/")
def root():
    return {"status": "ok", "message": "Backend running"}


# ============================================================
# AUTH: REGISTER & LOGIN
# ============================================================
@app.post("/register")
def register(user: UserRegister):
    conn = db("users.db")
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM users WHERE username=? OR email=?", (user.username, user.email))
    if cur.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username or email exists")

    if user.role not in ["student", "teacher"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Role must be student or teacher")

    hashed = hash_password(user.password)

    cur.execute("""
        INSERT INTO users (username, email, password_hash, role, full_name)
        VALUES (?, ?, ?, ?, ?)
    """, (user.username, user.email, hashed, user.role, user.full_name))

    user_id = cur.lastrowid
    conn.commit()
    conn.close()

    token = create_access_token({
        "sub": str(user_id),
        "role": user.role,
        "username": user.username
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(user_id),
        "username": user.username,
        "role": user.role
    }


@app.post("/login")
def login(user: UserLogin):
    conn = db("users.db")
    cur = conn.cursor()

    cur.execute("SELECT user_id, password_hash, role, username FROM users WHERE username=?", (user.username,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user_id, hash_pw, role, username = row

    if not verify_password(user.password, hash_pw):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({
        "sub": str(user_id),
        "role": role,
        "username": username
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(user_id),
        "username": username,
        "role": role
    }


# ============================================================
# RESUME → SKILLS (STUDENT ONLY)
# ============================================================
@app.post("/extract-skills/")
async def extract_skills_api(request: Request, file: UploadFile = File(...)):
    user = get_current_user_from_request(request)

    if user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can upload resumes")

    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    if file.filename.lower().endswith(".pdf"):
        text = extract_text_from_pdf(temp_path)
    elif file.filename.lower().endswith(".docx"):
        text = extract_text_from_docx(temp_path)
    else:
        os.remove(temp_path)
        raise HTTPException(status_code=400, detail="Unsupported file type")

    os.remove(temp_path)

    name = extract_name(text)
    skills = extract_skills(text)

    return {"name": name, "skills": skills}


# ============================================================
# COURSE RECOMMENDATIONS (STUDENT)
# ============================================================
@app.post("/personalized-recommendations")
def personalized_recommend(req: dict, user=Depends(require_role(["student"]))):
    skill_levels = req.get("skill_levels", {})

    conn = db("courses.db")
    df = pd.read_sql_query("""
        SELECT c.course_id, c.course_name, cs.skill, cs.weight
        FROM courses c
        JOIN course_skills cs ON c.course_id = cs.course_id
    """, conn)
    conn.close()

    if df.empty:
        return {"recommendations": []}

    matrix = df.pivot_table(
        index=["course_id", "course_name"],
        columns="skill",
        values="weight",
        fill_value=0,
    )

    skills = matrix.columns.tolist()
    user_vec = [skill_levels.get(s, 0) for s in skills]

    sims = cosine_similarity([user_vec], matrix.values)[0]

    recs = []
    for idx, (cid, cname) in enumerate(matrix.index):
        recs.append({
            "course_name": cname,
            "score": float(sims[idx]),
            "description": "Recommended based on your skill profile."
        })

    recs.sort(key=lambda x: x["score"], reverse=True)
    return {"recommendations": recs}


# ============================================================
# COURSE MANAGEMENT (TEACHER + GENERIC)
# ============================================================
@app.post("/add-course")
def add_course(req: dict, user=Depends(require_role(["teacher"]))):
    name = req.get("course_name")
    details = req.get("course_details", "")

    if not name:
        raise HTTPException(status_code=400, detail="Course name required")

    conn = db("courses.db")
    cur = conn.cursor()

    cur.execute("INSERT INTO courses (course_name, course_details) VALUES (?, ?)", (name, details))
    cid = cur.lastrowid

    # simple auto-skill extraction from description
    skills = extract_skills(details)
    for s in skills:
        cur.execute("""
            INSERT INTO course_skills (course_id, skill, weight)
            VALUES (?, ?, ?)
        """, (cid, s, 5.0))

    conn.commit()
    conn.close()

    return {"message": "Course added", "course_id": cid}

@app.put("/courses/{course_id}")
def update_course(course_id: int, payload: CourseUpdate, user=Depends(require_role(["teacher"]))):
    conn = db("courses.db")
    cur = conn.cursor()

    cur.execute("SELECT course_name, course_details FROM courses WHERE course_id=?", (course_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Course not found")

    current_name, current_details = row
    new_name = payload.course_name or current_name
    new_details = payload.course_details if payload.course_details is not None else current_details

    cur.execute(
        "UPDATE courses SET course_name=?, course_details=? WHERE course_id=?",
        (new_name, new_details, course_id),
    )
    conn.commit()
    conn.close()

    return {"message": "Course updated successfully"}



@app.get("/courses")
def get_courses(user=Depends(get_current_user)):
    conn = db("courses.db")
    cur = conn.cursor()
    cur.execute("SELECT course_id, course_name, course_details FROM courses")
    rows = cur.fetchall()
    conn.close()

    return {
        "courses": [
            {"course_id": r[0], "course_name": r[1], "course_details": r[2] or ""}
            for r in rows
        ]
    }

@app.delete("/courses/{course_id}/delete")
def delete_course(course_id: int, user=Depends(require_role(["teacher"]))):
    conn = db("courses.db")
    cur = conn.cursor()

    try:
        # Delete notes
        cur.execute("""
            DELETE FROM lesson_notes 
            WHERE lesson_id IN (
                SELECT lesson_id FROM lessons 
                WHERE module_id IN (
                    SELECT module_id FROM modules 
                    WHERE course_id=?
                )
            )
        """, (course_id,))

        # Delete progress
        cur.execute("""
            DELETE FROM lesson_progress 
            WHERE lesson_id IN (
                SELECT lesson_id FROM lessons 
                WHERE module_id IN (
                    SELECT module_id FROM modules 
                    WHERE course_id=?
                )
            )
        """, (course_id,))

        # Delete lessons
        cur.execute("""
            DELETE FROM lessons 
            WHERE module_id IN (
                SELECT module_id FROM modules 
                WHERE course_id=?
            )
        """, (course_id,))

        # Delete modules
        cur.execute("DELETE FROM modules WHERE course_id=?", (course_id,))

        # Delete course itself
        cur.execute("DELETE FROM courses WHERE course_id=?", (course_id,))

        conn.commit()
        return {"message": "Course deleted successfully"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        conn.close()




# ============================================================
# MODULE & LESSON MANAGEMENT (TEACHER)
# ============================================================
@app.post("/courses/{course_id}/add-module")
def add_module(course_id: int, req: dict, user=Depends(require_role(["teacher"]))):
    title = req.get("title")
    description = req.get("description", "")

    if not title:
        raise HTTPException(status_code=400, detail="Module title required")

    conn = db("courses.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO modules (course_id, title, description)
        VALUES (?, ?, ?)
    """, (course_id, title, description))
    conn.commit()
    conn.close()

    return {"message": "Module added successfully"}

@app.put("/modules/{module_id}")
def update_module(module_id: int, payload: ModuleUpdate, user=Depends(require_role(["teacher"]))):
    conn = db("courses.db")
    cur = conn.cursor()

    cur.execute("SELECT title, description FROM modules WHERE module_id=?", (module_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Module not found")

    current_title, current_desc = row
    new_title = payload.title or current_title
    new_desc = payload.description if payload.description is not None else current_desc

    cur.execute(
        "UPDATE modules SET title=?, description=? WHERE module_id=?",
        (new_title, new_desc, module_id),
    )
    conn.commit()
    conn.close()

    return {"message": "Module updated successfully"}




@app.post("/modules/{module_id}/add-lesson")
def add_lesson(module_id: int, req: dict, user=Depends(require_role(["teacher"]))):
    title = req.get("title")
    video_url = req.get("video_url")
    notes = req.get("notes", "")
    difficulty = req.get("difficulty", "Easy")
    github_url = req.get("github_url", "")

    if not title:
        raise HTTPException(status_code=400, detail="Lesson title required")

    conn = db("courses.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO lessons (module_id, title, video_url, notes, difficulty, github_url)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (module_id, title, video_url, notes, difficulty, github_url))
    conn.commit()
    conn.close()

    return {"message": "Lesson added successfully"}

@app.put("/lessons/{lesson_id}")
def update_lesson(lesson_id: int, payload: LessonUpdate, user=Depends(require_role(["teacher"]))):
    conn = db("courses.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT title, video_url, notes, difficulty, github_url
        FROM lessons
        WHERE lesson_id=?
    """, (lesson_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Lesson not found")

    current_title, current_vid, current_notes, current_diff, current_git = row

    new_title = payload.title or current_title
    new_vid = payload.video_url if payload.video_url is not None else current_vid
    new_notes = payload.notes if payload.notes is not None else current_notes
    new_diff = payload.difficulty or current_diff
    new_git = payload.github_url if payload.github_url is not None else current_git

    cur.execute("""
        UPDATE lessons
        SET title=?, video_url=?, notes=?, difficulty=?, github_url=?
        WHERE lesson_id=?
    """, (new_title, new_vid, new_notes, new_diff, new_git, lesson_id))

    conn.commit()
    conn.close()

    return {"message": "Lesson updated successfully"}


@app.get("/modules/{module_id}/lessons")
def get_lessons_for_module(module_id: int, user=Depends(require_role(["teacher"]))):
    conn = db("courses.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT lesson_id, title, video_url, notes, difficulty, order_index, github_url
        FROM lessons
        WHERE module_id=?
        ORDER BY order_index, lesson_id
    """, (module_id,))
    rows = cur.fetchall()
    conn.close()

    lessons = [
        {
            "lesson_id": r[0],
            "title": r[1],
            "video_url": r[2] or "",
            "notes": r[3] or "",
            "difficulty": r[4] or "Easy",
            "order_index": r[5],
            "github_url": r[6] or "",
        }
        for r in rows
    ]
    return {"lessons": lessons}



@app.get("/courses/{course_id}/modules")
def get_modules(course_id: int, user=Depends(require_role(["teacher"]))):
    conn = db("courses.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT module_id, title, description, order_index
        FROM modules
        WHERE course_id=?
        ORDER BY order_index, module_id
    """, (course_id,))
    rows = cur.fetchall()
    conn.close()

    modules = [
        {
            "module_id": r[0],
            "title": r[1],
            "description": r[2] or "",
            "order_index": r[3]
        }
        for r in rows
    ]
    return {"modules": modules}


# ============================================================
# COURSE STRUCTURE + PROGRESS (FOR STUDENTS)
# ============================================================
@app.get("/courses/{course_id}/structure")
def get_course_structure(course_id: int, user=Depends(get_current_user)):
    """
    Returns modules + lessons + student's completion state.
    Used by Study Dashboard.
    """
    conn = db("courses.db")
    cur = conn.cursor()

    # Modules
    cur.execute("""
        SELECT module_id, title, description, order_index
        FROM modules
        WHERE course_id=?
        ORDER BY order_index, module_id
    """, (course_id,))
    modules_rows = cur.fetchall()

    # Lessons + progress
    cur.execute("""
        SELECT 
            l.lesson_id, l.module_id, l.title, l.video_url, l.notes, l.difficulty, l.order_index, l.github_url, 
            COALESCE(lp.completed, 0) AS completed
        FROM lessons l
        LEFT JOIN lesson_progress lp
            ON lp.lesson_id = l.lesson_id AND lp.user_id = ?
        WHERE l.module_id IN (
            SELECT module_id FROM modules WHERE course_id = ?
        )
        ORDER BY l.module_id, l.order_index, l.lesson_id
    """, (user["user_id"], course_id))
    lessons_rows = cur.fetchall()
    conn.close()

    module_map: Dict[int, Dict[str, Any]] = {}
    for mid, title, desc, order_idx in modules_rows:
        module_map[mid] = {
            "module_id": mid,
            "title": title,
            "description": desc or "",
            "order_index": order_idx,
            "lessons": [],
            "completed_lessons": 0,
            "total_lessons": 0,
        }

    for (lesson_id, module_id, title, video_url, notes, difficulty,
         order_idx, github_url, completed) in lessons_rows:

        if module_id not in module_map:
            continue
        m = module_map[module_id]
        m["total_lessons"] += 1
        if completed:
            m["completed_lessons"] += 1

        m["lessons"].append({
            "lesson_id": lesson_id,
            "title": title,
            "video_url": video_url,
            "notes": notes or "",
            "difficulty": difficulty or "Easy",
            "order_index": order_idx,
            "github_url": github_url or "",
            "completed": bool(completed),
        })

    modules = []
    for mid in sorted(module_map, key=lambda x: module_map[x]["order_index"]):
        m = module_map[mid]
        if m["total_lessons"]:
            m["progress_percent"] = int(
                100 * m["completed_lessons"] / m["total_lessons"]
            )
        else:
            m["progress_percent"] = 0
        modules.append(m)

    return {"modules": modules}


# ============================================================
# PROGRESS & NOTES (STUDENT)
# ============================================================
@app.post("/lessons/{lesson_id}/progress")
def update_progress(lesson_id: int, p: ProgressUpdate,
                    user=Depends(require_role(["student"]))):
    conn = db("courses.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO lesson_progress (user_id, lesson_id, completed, last_opened)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, lesson_id)
        DO UPDATE SET completed=excluded.completed,
                      last_opened=excluded.last_opened
    """, (user["user_id"], lesson_id, int(p.completed), datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return {"message": "Progress updated"}


@app.post("/lessons/{lesson_id}/notes")
def update_notes(lesson_id: int, n: NoteUpdate,
                 user=Depends(require_role(["student"]))):
    conn = db("courses.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO lesson_notes (user_id, lesson_id, notes, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, lesson_id)
        DO UPDATE SET notes=excluded.notes,
                      updated_at=excluded.updated_at
    """, (user["user_id"], lesson_id, n.notes, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return {"message": "Notes saved"}


# ============================================================
# RUN SERVER
# ============================================================
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
