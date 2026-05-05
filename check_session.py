import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

session_id = "b63abe78-4545-4876-bbc3-1d91b58c7759"

print(f"Checking session: {session_id}")

res = db.execute(text(f"SELECT * FROM attendance_sessions WHERE id = '{session_id}'")).fetchone()
if res:
    print(f"FOUND Session: {res}")
    # Check related tables
    sub_id = res.subject_id
    room_id = res.classroom_id
    fac_id = res.faculty_id

    sub = db.execute(text(f"SELECT name FROM subjects WHERE id = '{sub_id}'")).fetchone()
    print(f"Subject ({sub_id}): {sub}")

    room = db.execute(text(f"SELECT name FROM classrooms WHERE id = '{room_id}'")).fetchone()
    print(f"Classroom ({room_id}): {room}")

    user = db.execute(text(f"SELECT full_name FROM app_users WHERE id = '{fac_id}'")).fetchone()
    print(f"User ({fac_id}): {user}")
else:
    print("Session NOT FOUND in attendance_sessions table.")

db.close()
