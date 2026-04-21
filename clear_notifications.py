import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

def clear_notifications(user_id):
    try:
        # Load database URL
        db_url = os.getenv("DATABASE_URL")

        # Check if local SQLite exists as fallback
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(script_dir, "attendance.db")

        urls_to_clean = []
        if db_url:
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)
            urls_to_clean.append((db_url, "Cloud Database"))

        if os.path.exists(db_path):
            urls_to_clean.append((f"sqlite:///{db_path}", "Local SQLite"))

        if not urls_to_clean:
            print("Error: No database connection found.")
            return

        print(f"\n" + "="*40)
        print(f"CLEARING NOTIFICATIONS FOR: {user_id}")
        print("="*40)

        for url, name in urls_to_clean:
            try:
                engine = create_engine(url)
                with engine.connect() as conn:
                    # Delete notifications for user
                    # We handle both ID and Username scenarios
                    sql = text("""
                        DELETE FROM notifications
                        WHERE user_id = :uid
                        OR user_id = (SELECT id FROM app_users WHERE username = :uid)
                    """)
                    result = conn.execute(sql, {"uid": user_id})
                    conn.commit()
                    print(f"[{name}] Success: {result.rowcount} notifications deleted.")
            except Exception as e:
                print(f"[{name}] Error: {e}")

        print("="*40)
        print(f"PROCESS FINISHED")
        print("="*40 + "\n")

    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        user = input("Enter Username/ID to clear notifications: ")
        if user: clear_notifications(user)
    else:
        clear_notifications(sys.argv[1])
