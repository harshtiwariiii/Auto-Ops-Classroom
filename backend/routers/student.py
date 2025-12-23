# routers/student.py
from fastapi import APIRouter, HTTPException, UploadFile, File, Request, Depends
from datetime import datetime
import os
import pandas as pd
import sqlite3

from utils.database import db
from utils.jwt_handler import decode_token
from routers.auth import get_current_user
from utils.skill_extractor import extract_name, extract_skills, extract_text_from_pdf, extract_text_from_docx
from sklearn.metrics.pairwise import cosine_similarity


router = APIRouter(prefix="/student", tags=["Student"])


# ---------------------------------------------
# ROLE CHECKER (only students allowed)
# ---------------------------------------------
def require_student(user=Depends(get_current_user)):
    if user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")
    return user


# ============================================================
# 📌 UPLOAD RESUME → EXTRACT SKILLS
# ============================================================
@router.post("/extract-skills/")
async def extract_skills_api(request: Request, file: UploadFile = File(...)):
    user = require_student(get_current_user(request))

    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    # Extract text based on file type
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
# 📌 PERSONALIZED COURSE RECOMMENDATIONS
# ============================================================
@router.post("/recommendations")
def personalized_recommend(req: dict, user=Depends(require_student)):
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

    # Build user vector
    user_vec = [skill_levels.get(s, 0) for s in skills]

    # Cosine similarity
    sims = cosine_similarity([user_vec], matrix.values)[0]

    recs = []
    for idx, (cid, cname) in enumerate(matrix.index):
        recs.append({
            "course_name": cname,
            "course_id": cid,
            "score": float(sims[idx]),
            "description": "Recommended based on your skill profile."
        })

    recs.sort(key=lambda x: x["score"], reverse=True)
    return {"recommendations": recs}


# ============================================================
# 📌 STUDENT COURSE STRUCTURE (modules + lessons)
# ============================================================
@router.get("/course/{course_id}")
def get_course_structure(course_id: int, user=Depends(require_student)):
    conn = db("courses.db")
    cur = conn.cursor()

    # Fetch modules
    cur.execute("""
        SELECT module_id, title, description, order_index
        FROM modules
        WHERE course_id=?
        ORDER BY order_index, module_id
    """, (course_id,))
    modules = cur.fetchall()

    # Fetch lessons + progress
    cur.execute("""
        SELECT 
            l.lesson_id, l.module_id, l.title, l.video_url, l.notes,
            l.difficulty, l.order_index, l.github_url,
            COALESCE(lp.completed, 0)
        FROM lessons l
        LEFT JOIN lesson_progress lp
            ON lp.lesson_id = l.lesson_id AND lp.user_id = ?
        WHERE l.module_id IN (SELECT module_id FROM modules WHERE course_id=?)
        ORDER BY l.module_id, l.order_index
    """, (user["user_id"], course_id))
    lessons = cur.fetchall()
    conn.close()

    # Mapping
    module_map = {}
    for mid, title, desc, order_idx in modules:
        module_map[mid] = {
            "module_id": mid,
            "title": title,
            "description": desc or "",
            "order_index": order_idx,
            "lessons": [],
            "completed_lessons": 0,
            "total_lessons": 0,
        }

    # Insert lessons
    for (
        lesson_id, module_id, title, video_url, notes,
        difficulty, order_idx, github_url, completed
    ) in lessons:

        m = module_map[module_id]
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

        m["total_lessons"] += 1
        if completed:
            m["completed_lessons"] += 1

    # Final response
    final_modules = []
    for m in module_map.values():
        m["progress_percent"] = (
            int(100 * m["completed_lessons"] / m["total_lessons"])
            if m["total_lessons"] else 0
        )
        final_modules.append(m)

    return {"modules": sorted(final_modules, key=lambda x: x["order_index"])}


# ============================================================
# 📌 STUDENT UPDATES PROGRESS
# ============================================================
@router.post("/lesson/{lesson_id}/progress")
def update_progress(lesson_id: int, req: dict, user=Depends(require_student)):
    completed = req.get("completed")
    if completed is None:
        raise HTTPException(status_code=400, detail="Missing 'completed' value")

    conn = db("courses.db")
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO lesson_progress (user_id, lesson_id, completed, last_opened)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, lesson_id)
        DO UPDATE SET completed=excluded.completed,
                      last_opened=excluded.last_opened
    """, (user["user_id"], lesson_id, int(completed), datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()

    return {"message": "Progress updated"}


# ============================================================
# 📌 STUDENT SAVES NOTES
# ============================================================
@router.post("/lesson/{lesson_id}/notes")
def save_notes(lesson_id: int, req: dict, user=Depends(require_student)):
    notes = req.get("notes", "")

    conn = db("courses.db")
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO lesson_notes (user_id, lesson_id, notes, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, lesson_id)
        DO UPDATE SET notes=excluded.notes,
                      updated_at=excluded.updated_at
    """, (user["user_id"], lesson_id, notes, datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()

    return {"message": "Notes saved"}
