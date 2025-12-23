# routers/courses.py
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any
import pandas as pd
import sqlite3

from utils.database import db
from utils.jwt_handler import decode_token
from routers.auth import get_current_user
from utils.skill_extractor import extract_skills
from pydantic import BaseModel

router = APIRouter(prefix="/courses", tags=["Courses"])


# ---------------------------------------------
# Pydantic Models
# ---------------------------------------------
class CourseCreate(BaseModel):
    course_name: str
    course_details: str | None = ""


class CourseUpdate(BaseModel):
    course_name: str | None = None
    course_details: str | None = None


# ---------------------------------------------
# Role checker
# ---------------------------------------------
def require_teacher(user=Depends(get_current_user)):
    if user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can access this")
    return user


# ---------------------------------------------
# 📌 Get All Courses
# ---------------------------------------------
@router.get("/")
def get_all_courses(user=Depends(get_current_user)):
    conn = db("courses.db")
    cur = conn.cursor()

    cur.execute("SELECT course_id, course_name, course_details FROM courses")
    rows = cur.fetchall()
    conn.close()

    return {
        "courses": [
            {
                "course_id": r[0],
                "course_name": r[1],
                "course_details": r[2] or ""
            }
            for r in rows
        ]
    }


# ---------------------------------------------
# 📌 Add a New Course (Teacher Only)
# ---------------------------------------------
@router.post("/add")
def add_course(payload: CourseCreate, user=Depends(require_teacher)):
    if not payload.course_name:
        raise HTTPException(status_code=400, detail="Course name required")

    conn = db("courses.db")
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO courses (course_name, course_details) VALUES (?, ?)",
        (payload.course_name, payload.course_details)
    )
    course_id = cur.lastrowid

    # Auto skill extraction from description
    skills = extract_skills(payload.course_details or "")
    for s in skills:
        cur.execute(
            """
            INSERT INTO course_skills (course_id, skill, weight)
            VALUES (?, ?, ?)
            """,
            (course_id, s, 5.0)
        )

    conn.commit()
    conn.close()

    return {"message": "Course created", "course_id": course_id}


# ---------------------------------------------
# 📌 Update a Course (Teacher Only)
# ---------------------------------------------
@router.put("/{course_id}")
def update_course(course_id: int, payload: CourseUpdate, user=Depends(require_teacher)):
    conn = db("courses.db")
    cur = conn.cursor()

    cur.execute("SELECT course_name, course_details FROM courses WHERE course_id=?", (course_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Course not found")

    new_name = payload.course_name or row[0]
    new_details = payload.course_details if payload.course_details is not None else row[1]

    cur.execute(
        "UPDATE courses SET course_name=?, course_details=? WHERE course_id=?",
        (new_name, new_details, course_id)
    )

    conn.commit()
    conn.close()

    return {"message": "Course updated"}


# ---------------------------------------------
# 🗑 Delete a Course + All Modules + Lessons
# ---------------------------------------------
@router.delete("/{course_id}/delete")
def delete_course(course_id: int, user=Depends(require_teacher)):
    conn = db("courses.db")
    cur = conn.cursor()

    try:
        # Delete notes
        cur.execute("""
            DELETE FROM lesson_notes WHERE lesson_id IN (
                SELECT lesson_id FROM lessons WHERE module_id IN (
                    SELECT module_id FROM modules WHERE course_id=?
                )
            )
        """, (course_id,))

        # Delete progress
        cur.execute("""
            DELETE FROM lesson_progress WHERE lesson_id IN (
                SELECT lesson_id FROM lessons WHERE module_id IN (
                    SELECT module_id FROM modules WHERE course_id=?
                )
            )
        """, (course_id,))

        # Delete lessons
        cur.execute("""
            DELETE FROM lessons WHERE module_id IN (
                SELECT module_id FROM modules WHERE course_id=?
            )
        """, (course_id,))

        # Delete modules
        cur.execute("DELETE FROM modules WHERE course_id=?", (course_id,))

        # Delete course
        cur.execute("DELETE FROM courses WHERE course_id=?", (course_id,))

        conn.commit()
        return {"message": "Course deleted"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        conn.close()


# ---------------------------------------------
# 📌 Get Modules for a Course (Teacher Only)
# ---------------------------------------------
@router.get("/{course_id}/modules")
def get_modules(course_id: int, user=Depends(require_teacher)):
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

    return {
        "modules": [
            {
                "module_id": r[0],
                "title": r[1],
                "description": r[2] or "",
                "order_index": r[3],
            }
            for r in rows
        ]
    }


# ---------------------------------------------
# 📌 Full Course Structure (Student Dashboard)
# ---------------------------------------------
@router.get("/{course_id}/structure")
def get_course_structure(course_id: int, user=Depends(get_current_user)):
    conn = db("courses.db")
    cur = conn.cursor()

    # Fetch modules
    cur.execute("""
        SELECT module_id, title, description, order_index
        FROM modules WHERE course_id=?
        ORDER BY order_index
    """, (course_id,))
    modules = cur.fetchall()

    # Fetch lessons + progress
    cur.execute("""
        SELECT 
            l.lesson_id, l.module_id, l.title, l.video_url, l.notes, l.difficulty,
            l.order_index, l.github_url,
            COALESCE(lp.completed, 0)
        FROM lessons l
        LEFT JOIN lesson_progress lp
            ON lp.lesson_id = l.lesson_id AND lp.user_id = ?
        WHERE l.module_id IN (SELECT module_id FROM modules WHERE course_id=?)
        ORDER BY l.module_id, l.order_index
    """, (user["user_id"], course_id))
    lessons = cur.fetchall()

    conn.close()

    # Build structure
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

    for (
        lesson_id, module_id, title, video_url, notes, difficulty,
        order_idx, github_url, completed
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

    # Add progress %
    final_modules = []
    for m in module_map.values():
        if m["total_lessons"]:
            m["progress_percent"] = int(100 * m["completed_lessons"] / m["total_lessons"])
        else:
            m["progress_percent"] = 0

        final_modules.append(m)

    return {"modules": sorted(final_modules, key=lambda x: x["order_index"])}
