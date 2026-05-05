
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not found")
    exit()

db_url = db_url.replace("postgres://", "postgresql://", 1)
engine = create_engine(db_url)

with engine.connect() as conn:
    print("--- USERS ---")
    res = conn.execute(text("SELECT id, username, full_name, role FROM app_users WHERE username ILIKE '%nikam%' OR id ILIKE '%nikam%' OR username = '241080017'"))
    for row in res:
        print(row)

    print("\n--- TEACHERS ---")
    res = conn.execute(text("SELECT id, department_id, branch FROM app_teachers WHERE id IN (SELECT id FROM app_users WHERE username ILIKE '%nikam%' OR username = '241080017')"))
    for row in res:
        print(row)

    print("\n--- SUBJECTS ---")
    res = conn.execute(text("SELECT id, name, branch, year, department_id FROM subjects WHERE id = 'aa7b996b-2831-4d48-8cd5-8e2b4064ee95' OR branch = 'IT'"))
    for row in res:
        print(row)

    print("\n--- SESSIONS COUNT ---")
    res = conn.execute(text("SELECT faculty_id, count(*) FROM attendance_sessions GROUP BY faculty_id"))
    for row in res:
        print(row)

    print("\n--- SAMPLE SESSION ---")
    res = conn.execute(text("SELECT s.id, s.faculty_id, s.subject_id, s.start_time, sub.branch, sub.year FROM attendance_sessions s JOIN subjects sub ON s.subject_id = sub.id LIMIT 5"))
    for row in res:
        print(row)
