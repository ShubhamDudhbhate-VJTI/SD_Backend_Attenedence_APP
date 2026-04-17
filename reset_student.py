import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

def reset_in_db(db_url, name, roll_no):
    try:
        if not db_url:
            print(f"Skipping {name}: No URL found.")
            return

        # Fix postgres prefix for SQLAlchemy 2.0+
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        engine = create_engine(db_url)
        with engine.connect() as conn:
            print(f"--- Accessing {name} ---")

            # 1. Ensure columns exist (especially for local SQLite which metadata.create_all doesn't update)
            try:
                if "sqlite" in db_url:
                    conn.execute(text("ALTER TABLE app_students ADD COLUMN face_image BLOB;"))
                    conn.commit()
                    print(f"Added face_image column to {name}")
            except Exception:
                pass # Already exists

            # 2. Wipe data
            sql = text("""
                UPDATE app_students
                SET face_embedding = NULL, face_image = NULL
                WHERE registration_number = :roll_no
                OR id = (SELECT id FROM app_users WHERE username = :roll_no)
            """)
            result = conn.execute(sql, {"roll_no": roll_no})
            conn.commit()
            print(f"Success: {result.rowcount} rows reset in {name}.")
    except Exception as e:
        print(f"Error resetting {name}: {e}")

def run_full_wipe(roll_no):
    print(f"\n" + "="*40)
    print(f"GLOBAL WIPE FOR ROLL NO: {roll_no}")
    print("="*40)

    # 1. Wipe Supabase
    supabase_url = os.getenv("DATABASE_URL")
    reset_in_db(supabase_url, "SUPABASE CLOUD", roll_no)

    # 2. Wipe Local SQLite
    # We look for attendance.db in the backend folder relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "attendance.db")
    local_sqlite_url = f"sqlite:///{db_path}"
    reset_in_db(local_sqlite_url, "LOCAL SQLITE (attendance.db)", roll_no)

    # 3. Wipe Local Filesystem
    faces_dir = os.path.join(script_dir, "static", "faces")
    local_file = os.path.join(faces_dir, f"{roll_no}.jpg")
    if os.path.exists(local_file):
        try:
            os.remove(local_file)
            print(f"Deleted local image file: {local_file}")
        except Exception as e:
            print(f"Could not delete image file: {e}")
    else:
        print(f"No local image file found for {roll_no}")

    print("="*40)
    print(f"WIPE PROCESS FINISHED")
    print("="*40 + "\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        roll = input("Enter Roll Number to wipe: ")
        if roll: run_full_wipe(roll)
    else:
        run_full_wipe(sys.argv[1])
