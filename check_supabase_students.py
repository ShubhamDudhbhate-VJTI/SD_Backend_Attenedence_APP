
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://", 1)
engine = create_engine(db_url)

with engine.connect() as conn:
    print("--- STUDENT BRANCHES ---")
    res = conn.execute(text("SELECT DISTINCT branch FROM app_students"))
    for row in res:
        print(row)

    print("\n--- STUDENT YEARS ---")
    res = conn.execute(text("SELECT DISTINCT year FROM app_students"))
    for row in res:
        print(row)

    print("\n--- IT SECOND YEAR STUDENTS ---")
    res = conn.execute(text("SELECT count(*) FROM app_students WHERE (branch ILIKE '%IT%' OR department_id ILIKE '%IT%') AND year ILIKE '%Second Year%'"))
    print(f"Count: {res.fetchone()[0]}")

    print("\n--- SESSIONS FOR VBNIKAM IN RANGE ---")
    # April 25 to May 15, 2026
    res = conn.execute(text("""
        SELECT count(*)
        FROM attendance_sessions s
        JOIN subjects sub ON s.subject_id = sub.id
        WHERE (s.faculty_id = 'VBNIKAM' OR s.faculty_id = 'vbnikam')
        AND s.start_time >= '2026-04-25'
        AND s.start_time <= '2026-05-16'
    """))
    print(f"Count: {res.fetchone()[0]}")

    print("\n--- SUBJECTS FOR IT ---")
    res = conn.execute(text("SELECT id, name, branch, year FROM subjects WHERE branch ILIKE '%IT%'"))
    for row in res:
        print(row)
