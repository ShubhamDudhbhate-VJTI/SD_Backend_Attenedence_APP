import os
from sqlalchemy import create_engine, text
from main import Base, DATABASE_URL
from import_faculty import upload_teachers
from import_students import upload_students
from import_classrooms import upload_classrooms
from update_ssids import update_ssids

def init_database():
    print(f"--- Initializing New Database ---")
    engine = create_engine(DATABASE_URL)

    # 1. Create all base tables from SQLAlchemy models
    print("Creating tables...")
    Base.metadata.create_all(engine)

    # 2. Apply manual schema extensions
    with engine.connect() as conn:
        print("Applying schema extensions...")
        # Faculty Extensions
        conn.execute(text("ALTER TABLE app_teachers ADD COLUMN IF NOT EXISTS designation TEXT;"))
        conn.execute(text("ALTER TABLE app_teachers ADD COLUMN IF NOT EXISTS qualification TEXT;"))
        conn.execute(text("ALTER TABLE app_teachers ADD COLUMN IF NOT EXISTS specialization TEXT;"))
        conn.execute(text("ALTER TABLE app_teachers ADD COLUMN IF NOT EXISTS phone TEXT;"))

        # Mapping Tables
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS faculty_subjects (
                id TEXT PRIMARY KEY,
                faculty_id TEXT REFERENCES app_users(id),
                subject_id TEXT REFERENCES subjects(id)
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS branch_subjects (
                id TEXT PRIMARY KEY,
                branch TEXT,
                year TEXT,
                subject_id TEXT REFERENCES subjects(id)
            );
        """))

        # Enrollment cleanup
        conn.execute(text("ALTER TABLE enrollments DROP COLUMN IF EXISTS is_minor;"))
        conn.commit()

    print("--- Basic Schema Ready ---")

    # 3. Re-import data
    print("Importing Faculty (199 records)...")
    upload_teachers()

    print("Importing Students (700+ records)...")
    upload_students()

    print("Importing Classrooms (50 records)...")
    upload_classrooms()

    print("Customizing WiFi SSIDs...")
    update_ssids()

    print("\nSUCCESS: Entire Database recreated and populated (Faculty, Students, and Classrooms).")

if __name__ == "__main__":
    init_database()
