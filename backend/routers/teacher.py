# routers/teacher.py

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any
from utils.database import db
from routers.auth import require_role
from utils.skill_extractor import extract_skills


router = APIRouter(prefix="/teacher", tags=["Teacher"])


# ==================================================================
# 🧑‍🏫 TEACHER — ADD COURSE
# ==================================================================
@router.post("/course/add")
def add_course(req: Dict[str, Any], user=Depends(require_role(["teacher"]))):
    name = req.get("course_name")
    details = req.get("course_details", "")

    if not name:
        raise HTTPException(status_code=400, detail="Course name required")

    conn = db("courses.db")
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO courses (course_name, course_details) VALUES (?, ?)",
        (name, details)
    )

    course_id = cur.lastrowid

    # Auto skill extraction from description
    skills = extract_skills(details)
    for skill in skills:
        cur.execute(
            """
            INSERT INTO course_skills (course_id, skill, weight)
            VALUES (?, ?, ?)
            """,
            (course_id, skill, 5.0)
        )

    conn.commit()
    conn.close()

    return {"message": "Course added", "course_id": course_id}


# ==================================================================
# 🧑‍🏫 TEACHER — UPDATE COURSE
# ==================================================================
@router.put("/course/{course_id}")
def update_course(course_id: int, req: Dict[str, Any], user=Depends(require_role(["teacher"]))):
    new_name = req.get("course_name")
    new_details = req.get("course_details")

    conn = db("courses.db")
    cur = conn.cursor()

    cur.execute("SELECT course_name, course_details FROM courses WHERE course_id=?", (course_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Course not found")

    cur.execute(
        "UPDATE courses SET course_name=?, course_details=? WHERE course_id=?",
        (new_name or row[0], new_details or row[1], course_id)
    )

    conn.commit()
    conn.close()

    return {"message": "Course updated successfully"}


# ==================================================================
# 🧑‍🏫 TEACHER — DELETE COURSE (CASCADE DELETE)
# ==================================================================
@router.delete("/course/{course_id}/delete")
def delete_course(course_id: int, user=Depends(require_role(["teacher"]))):
    conn = db("courses.db")
    cur = conn.cursor()

    try:
        # Delete notes
        cur.execute("""
            DELETE FROM lesson_notes
            WHERE lesson_id IN (
                SELECT lesson_id FROM lessons WHERE module_id IN (
                    SELECT module_id FROM modules WHERE course_id=?
                )
            )
        """, (course_id,))

        # Delete progress
        cur.execute("""
            DELETE FROM lesson_progress
            WHERE lesson_id IN (
                SELECT lesson_id FROM lessons WHERE module_id IN (
                    SELECT module_id FROM modules WHERE course_id=?
                )
            )
        """, (course_id,))

        # Delete lessons
        cur.execute("""
            DELETE FROM lessons
            WHERE module_id IN (
                SELECT module_id FROM modules WHERE course_id=?
            )
        """, (course_id,))

        # Delete modules
        cur.execute("DELETE FROM modules WHERE course_id=?", (course_id,))

        # Delete course
        cur.execute("DELETE FROM courses WHERE course_id=?", (course_id,))

        conn.commit()
        return {"message": "Course deleted successfully"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        conn.close()


# ==================================================================
# 🧑‍🏫 TEACHER — GET ALL COURSES (NO STUDENT FILTER)
# ==================================================================
@router.get("/courses")
def view_courses(user=Depends(require_role(["teacher"]))):
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


# ==================================================================
# 🧑‍🏫 TEACHER — ADD MODULE
# ==================================================================
@router.post("/course/{course_id}/module/add")
def add_module(course_id: int, req: Dict[str, Any], user=Depends(require_role(["teacher"]))):
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


# ==================================================================
# 🧑‍🏫 TEACHER — UPDATE MODULE
# ==================================================================
@router.put("/module/{module_id}")
def update_module(module_id: int, req: Dict[str, Any], user=Depends(require_role(["teacher"]))):
    title = req.get("title")
    description = req.get("description")

    conn = db("courses.db")
    cur = conn.cursor()

    cur.execute("SELECT title, description FROM modules WHERE module_id=?", (module_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Module not found")

    cur.execute("""
        UPDATE modules SET title=?, description=? WHERE module_id=?
    """, (title or row[0], description or row[1], module_id))

    conn.commit()
    conn.close()

    return {"message": "Module updated successfully"}


# ==================================================================
# 🧑‍🏫 TEACHER — GET MODULES
# ==================================================================
@router.get("/course/{course_id}/modules")
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

    return {
        "modules": [
            {
                "module_id": r[0],
                "title": r[1],
                "description": r[2] or "",
                "order_index": r[3]
            }
            for r in rows
        ]
    }


# ==================================================================
# 🧑‍🏫 TEACHER — ADD LESSON
# ==================================================================
@router.post("/module/{module_id}/lesson/add")
def add_lesson(module_id: int, req: Dict[str, Any], user=Depends(require_role(["teacher"]))):
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


# ==================================================================
# 🧑‍🏫 TEACHER — UPDATE LESSON
# ==================================================================
@router.put("/lesson/{lesson_id}")
def update_lesson(lesson_id: int, req: Dict[str, Any], user=Depends(require_role(["teacher"]))):
    conn = db("courses.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT title, video_url, notes, difficulty, github_url
        FROM lessons WHERE lesson_id=?
    """, (lesson_id,))

    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Lesson not found")

    new_title = req.get("title") or row[0]
    new_vid = req.get("video_url") if req.get("video_url") is not None else row[1]
    new_notes = req.get("notes") if req.get("notes") is not None else row[2]
    new_diff = req.get("difficulty") or row[3]
    new_git = req.get("github_url") if req.get("github_url") is not None else row[4]

    cur.execute("""
        UPDATE lessons
        SET title=?, video_url=?, notes=?, difficulty=?, github_url=?
        WHERE lesson_id=?
    """, (new_title, new_vid, new_notes, new_diff, new_git, lesson_id))

    conn.commit()
    conn.close()

    return {"message": "Lesson updated successfully"}


# ==================================================================
# 🧑‍🏫 TEACHER — GET LESSONS
# ==================================================================
@router.get("/module/{module_id}/lessons")
def get_lessons(module_id: int, user=Depends(require_role(["teacher"]))):
    conn = db("courses.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT lesson_id, title, video_url, notes, difficulty,
               order_index, github_url
        FROM lessons
        WHERE module_id=?
        ORDER BY order_index, lesson_id
    """, (module_id,))

    rows = cur.fetchall()
    conn.close()

    return {
        "lessons": [
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
    }
