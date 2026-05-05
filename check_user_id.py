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
res = db.execute(text(f"SELECT id, username, full_name FROM app_users WHERE id = '{user_id}'")).fetchone()
print(f"User with ID '{user_id}': {res}")

res_lower = db.execute(text(f"SELECT id, username, full_name FROM app_users WHERE id ILIKE '{user_id}'")).fetchone()
print(f"User with ID ILIKE '{user_id}': {res_lower}")

db.close()
