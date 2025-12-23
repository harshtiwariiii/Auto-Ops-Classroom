# utils/database.py

import sqlite3
from pathlib import Path

# Base directory of backend
BASE_DIR = Path(__file__).resolve().parent.parent

# Data folder path
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def db(path: str):
    """
    Returns a SQLite connection to a database file inside /data folder.

    Example:
        conn = db("users.db")
        cur = conn.cursor()
    """
    return sqlite3.connect(str(DATA_DIR / path), check_same_thread=False)


def init_databases():
    """
    Ensures the required databases exist with correct tables.
    This function can be called inside main.py at startup.
    """

    # ---------------------------------------------------------
    # USERS DATABASE
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # COURSES DATABASE
    # ---------------------------------------------------------
    conn_c = db("courses.db")
    cur_c = conn_c.cursor()

    # Courses
    cur_c.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            course_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name    TEXT NOT NULL,
            course_details TEXT
        )
    """)

    # Course skills for recommendation engine
    cur_c.execute("""
        CREATE TABLE IF NOT EXISTS course_skills (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            skill     TEXT NOT NULL,
            weight    REAL NOT NULL,
            FOREIGN KEY(course_id) REFERENCES courses(course_id)
        )
    """)

    # Modules
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

    # Lessons
    cur_c.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            lesson_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id      INTEGER NOT NULL,
            title          TEXT NOT NULL,
            video_url      TEXT,
            notes          TEXT,
            difficulty     TEXT,
            order_index    INTEGER DEFAULT 0,
            github_url     TEXT,
            FOREIGN KEY(module_id) REFERENCES modules(module_id)
        )
    """)

    # Student Lesson Progress
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

    # Student Lesson Notes
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


# Run initialization when module is imported
init_databases()
