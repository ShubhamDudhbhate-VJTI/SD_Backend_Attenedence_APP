import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def fix_db():
    print(f"Connecting to: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)

    migrations = [
        # app_users
        "ALTER TABLE app_users ADD COLUMN IF NOT EXISTS fcm_token TEXT",
        "ALTER TABLE app_users ADD COLUMN IF NOT EXISTS profile_photo BYTEA",

        # app_students
        "ALTER TABLE app_students ADD COLUMN IF NOT EXISTS face_image BYTEA",
        "ALTER TABLE app_students ADD COLUMN IF NOT EXISTS device_id TEXT",
        "ALTER TABLE app_students ADD COLUMN IF NOT EXISTS department_id TEXT",

        # attendance_records
        "ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS record_hash TEXT",
        "ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS latitude NUMERIC(9,6)",
        "ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS longitude NUMERIC(9,6)",
        "ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS face_verified BOOLEAN DEFAULT FALSE",
        "ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS wifi_bssid_matched TEXT",

        # classrooms
        "ALTER TABLE classrooms ADD COLUMN IF NOT EXISTS wifi_ssid TEXT",
        "ALTER TABLE classrooms ADD COLUMN IF NOT EXISTS wifi_bssid TEXT"
    ]

    for sql in migrations:
        with engine.connect() as conn:
            try:
                print(f"Executing: {sql}")
                conn.execute(text(sql))
                conn.commit()
                print("Success")
            except Exception as e:
                print(f"Already exists or Error: {e}")

    print("\nMigration finished.")

if __name__ == "__main__":
    fix_db()
