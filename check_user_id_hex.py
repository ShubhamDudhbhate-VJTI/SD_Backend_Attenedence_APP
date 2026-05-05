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

user_id = "VBNIKAM"
res = db.execute(text(f"SELECT id FROM app_users WHERE id ILIKE '{user_id}'")).fetchall()
for r in res:
    val = r[0]
    print(f"User ID: {repr(val)}, Hex: {val.encode('utf-8').hex()}")

print("\nSession Faculty IDs:")
res = db.execute(text(f"SELECT DISTINCT faculty_id FROM attendance_sessions")).fetchall()
for r in res:
    val = r[0]
    if val:
        print(f"Faculty ID in Sessions: {repr(val)}, Hex: {val.encode('utf-8').hex()}")

db.close()
