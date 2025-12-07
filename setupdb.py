import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "backend" / "data"

conn = sqlite3.connect(DATA_DIR / "courses.db")
cur = conn.cursor()

# MODULES (Steps)
cur.execute("""
CREATE TABLE IF NOT EXISTS modules (
    module_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id   INTEGER NOT NULL,
    title       TEXT NOT NULL,
    description TEXT,
    order_index INTEGER DEFAULT 0,
    FOREIGN KEY(course_id) REFERENCES courses(course_id)
);
""")

# LESSONS inside modules
cur.execute("""
CREATE TABLE IF NOT EXISTS lessons (
    lesson_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id      INTEGER NOT NULL,
    title          TEXT NOT NULL,
    video_url      TEXT,
    notes_url      TEXT,
    resources_url  TEXT,
    assignment_url TEXT,
    difficulty     TEXT,
    order_index    INTEGER DEFAULT 0,
    FOREIGN KEY(module_id) REFERENCES modules(module_id)
);
""")

# PROGRESS per user per lesson
cur.execute("""
CREATE TABLE IF NOT EXISTS lesson_progress (
    user_id     INTEGER NOT NULL,
    lesson_id   INTEGER NOT NULL,
    completed   INTEGER NOT NULL DEFAULT 0,
    last_opened TEXT,
    PRIMARY KEY(user_id, lesson_id),
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(lesson_id) REFERENCES lessons(lesson_id)
);
""")

# PERSONAL NOTES per user per lesson
cur.execute("""
CREATE TABLE IF NOT EXISTS lesson_notes (
    user_id    INTEGER NOT NULL,
    lesson_id  INTEGER NOT NULL,
    notes      TEXT,
    updated_at TEXT,
    PRIMARY KEY(user_id, lesson_id),
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(lesson_id) REFERENCES lessons(lesson_id)
);
""")

conn.commit()
conn.close()
