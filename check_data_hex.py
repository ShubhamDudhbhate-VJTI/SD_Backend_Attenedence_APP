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

res = db.execute(text(f"SELECT faculty_id FROM attendance_sessions WHERE id LIKE 'b63abe78%'")).fetchone()
if res:
    fid = res[0]
    print(f"Faculty ID: {repr(fid)}")
    print(f"Hex: {fid.encode('utf-8').hex()}")
else:
    print("Session not found")

db.close()
