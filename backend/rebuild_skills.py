import sqlite3
import spacy

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

SKILL_KEYWORDS = [
    "python", "aws", "cli", "networking", "docker", "linux", "git", "mlops",
    "devops", "java", "c++", "cloud", "azure", "gcp", "kubernetes",
    "terraform", "ansible", "sql", "nosql", "data science", "machine learning",
    "deep learning", "pandas", "numpy", "scikit-learn", "flask", "django",
    "rest api", "agile", "scrum"
]

def extract_skills(text):
    low = text.lower()
    return [skill for skill in SKILL_KEYWORDS if skill in low]

conn = sqlite3.connect("data/courses.db")
cur = conn.cursor()

# FIXED COLUMN HERE
cur.execute("SELECT course_id, course_details FROM courses")
rows = cur.fetchall()

for course_id, desc in rows:
    if not desc:
        continue

    # Extract skills
    skills = extract_skills(desc)

    # Delete old skills
    cur.execute("DELETE FROM course_skills WHERE course_id=?", (course_id,))

    # Insert new skills
    for s in skills:
        cur.execute(
            "INSERT INTO course_skills (course_id, skill, weight) VALUES (?, ?, ?)",
            (course_id, s, 5.0),
        )

conn.commit()
conn.close()

print("✔ Skill rebuild completed.")
