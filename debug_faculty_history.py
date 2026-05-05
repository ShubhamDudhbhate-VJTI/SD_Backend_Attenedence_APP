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

# List some recent sessions and their faculty_ids
print("Recent Sessions:")
sessions = db.execute(text("SELECT id, faculty_id, subject_id, start_time FROM attendance_sessions ORDER BY start_time DESC LIMIT 10")).fetchall()
for s in sessions:
    print(s)

# List some users
print("\nRecent Users:")
users = db.execute(text("SELECT id, username, role FROM app_users LIMIT 10")).fetchall()
for u in users:
    print(u)

db.close()
