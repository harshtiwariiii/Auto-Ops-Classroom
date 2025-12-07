import sqlite3
from pathlib import Path

# Correct path based on your folder structure
DB_PATH = Path(__file__).resolve().parent / "data" / "courses.db"

def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def fix_lessons_table():
    print(f"Opening database at: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("Checking lessons table...")

    # Add notes column if missing
    if not column_exists(cur, "lessons", "notes"):
        print("🛠 Adding missing column: notes")
        cur.execute("ALTER TABLE lessons ADD COLUMN notes TEXT")
        conn.commit()
    else:
        print("✔ notes column already exists")

    # Add difficulty column if missing
    if not column_exists(cur, "lessons", "difficulty"):
        print("🛠 Adding missing column: difficulty")
        cur.execute("ALTER TABLE lessons ADD COLUMN difficulty TEXT DEFAULT 'Easy'")
        conn.commit()
    else:
        print("✔ difficulty column already exists")

    conn.close()
    print("🎉 Database fix completed.")

if __name__ == "__main__":
    print("Running DB Fix...")
    fix_lessons_table()
    print("Done!")
