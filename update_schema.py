import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)
db_url = os.getenv('DATABASE_URL')
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url)

def update_schema():
    with engine.connect() as conn:
        print("Updating app_teachers...")
        conn.execute(text("ALTER TABLE app_teachers ADD COLUMN IF NOT EXISTS designation TEXT;"))
        conn.execute(text("ALTER TABLE app_teachers ADD COLUMN IF NOT EXISTS qualification TEXT;"))
        conn.execute(text("ALTER TABLE app_teachers ADD COLUMN IF NOT EXISTS specialization TEXT;"))
        conn.execute(text("ALTER TABLE app_teachers ADD COLUMN IF NOT EXISTS phone TEXT;"))

        print("Updating app_students...")
        conn.execute(text("ALTER TABLE app_students ADD COLUMN IF NOT EXISTS face_image BYTEA;"))

        print("Creating faculty_subjects table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS faculty_subjects (
                id TEXT PRIMARY KEY,
                faculty_id TEXT REFERENCES app_users(id),
                subject_id TEXT REFERENCES subjects(id)
            );
        """))

        print("Creating branch_subjects table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS branch_subjects (
                id TEXT PRIMARY KEY,
                branch TEXT,
                year TEXT,
                subject_id TEXT REFERENCES subjects(id)
            );
        """))

        print("Updating enrollments table (Minor Subjects)...")
        # Removing is_minor if it was added, as enrollment is now purely for minors
        try:
            conn.execute(text("ALTER TABLE enrollments DROP COLUMN IF EXISTS is_minor;"))
        except Exception:
            pass

        print("Updating schedules table...")
        conn.execute(text("ALTER TABLE schedules ADD COLUMN IF NOT EXISTS is_official BOOLEAN DEFAULT TRUE;"))

        conn.commit()
        print("Schema updated successfully.")

if __name__ == "__main__":
    update_schema()
