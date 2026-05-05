import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./attendance.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_hod_user():
    db = SessionLocal()
    try:
        # Check if HOD already exists
        check = db.execute(text("SELECT * FROM app_users WHERE username = 'hod_it'")).fetchone()
        if check:
            print("HOD user 'hod_it' already exists.")
            return

        user_id = str(uuid.uuid4())

        # 1. Create User entry
        db.execute(
            text("INSERT INTO app_users (id, username, email, password_hash, full_name, role) VALUES (:id, :u, :e, :p, :f, :r)"),
            {"id": user_id, "u": "hod_it", "e": "hod_it@vjti.ac.in", "p": "hod123", "f": "Dr. V. B. Nikam", "r": "hod"}
        )

        # 2. Create Teacher entry (HODs are stored in app_teachers table)
        # Note: employee_id must be unique
        db.execute(
            text("INSERT INTO app_teachers (id, employee_id, full_name, department_id, designation) VALUES (:id, :eid, :f, :dept, :desig)"),
            {"id": user_id, "eid": "EMP_HOD_IT", "f": "Dr. V. B. Nikam", "dept": "IT", "desig": "Professor & HOD"}
        )

        db.commit()
        print("--- SUCCESS: HOD User Created ---")
        print("Username: hod_it")
        print("Password: hod123")
        print("Role: hod")
        print("Department: IT")
    except Exception as e:
        print(f"Error creating HOD: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_hod_user()
