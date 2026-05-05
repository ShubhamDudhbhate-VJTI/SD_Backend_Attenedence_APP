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

def update_hod_user():
    db = SessionLocal()
    try:
        # Update User entry
        db.execute(
            text("UPDATE app_users SET full_name = :f, password_hash = :p WHERE username = 'hod_it'"),
            {"f": "Dr. V. B. Nikam", "p": "123456"}
        )

        # Update Teacher entry
        db.execute(
            text("UPDATE app_teachers SET full_name = :f WHERE id = (SELECT id FROM app_users WHERE username = 'hod_it')"),
            {"f": "Dr. V. B. Nikam"}
        )

        db.commit()
        print("--- SUCCESS: HOD User Updated ---")
        print("Username: hod_it")
        print("Password: 123456")
        print("Name: Dr. V. B. Nikam")
    except Exception as e:
        print(f"Error updating HOD: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_hod_user()
