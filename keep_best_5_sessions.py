
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not found")
    exit()

db_url = db_url.replace("postgres://", "postgresql://", 1)
engine = create_engine(db_url)

FACULTY_ID = 'VBNIKAM'

with engine.connect() as conn:
    # Get all faculty IDs
    faculties = conn.execute(text("SELECT id FROM app_users WHERE role = 'faculty'")).fetchall()
    faculty_ids = [f[0] for f in faculties]

    for fid in faculty_ids:
        print(f"\nProcessing Faculty: {fid}")
        # 1. Get all sessions for faculty with their student counts
        query = text("""
            SELECT s.id, COUNT(r.id) as actual_count, s.start_time
            FROM attendance_sessions s
            LEFT JOIN attendance_records r ON s.id = r.session_id
            WHERE s.faculty_id = :faculty_id
            GROUP BY s.id, s.start_time
            ORDER BY s.start_time DESC
        """)

        results = conn.execute(query, {"faculty_id": fid}).fetchall()

        if len(results) <= 5:
            print(f"  Only has {len(results)} sessions. Skipping.")
            continue

        # Logic: Latest 1 + Top 4 of the rest (sorted by count)
        latest_session = results[0]
        other_sessions = sorted(results[1:], key=lambda x: x[1], reverse=True)

        keep_sessions = [latest_session] + other_sessions[:4]
        keep_ids = [s[0] for s in keep_sessions]

        all_ids = [row[0] for row in results]
        delete_ids = [sid for sid in all_ids if sid not in keep_ids]

        print(f"  Keeping {len(keep_ids)} sessions, deleting {len(delete_ids)}.")

        if delete_ids:
            conn.execute(text("DELETE FROM attendance_records WHERE session_id IN :ids"), {"ids": tuple(delete_ids)})
            conn.execute(text("DELETE FROM attendance_sessions WHERE id IN :ids"), {"ids": tuple(delete_ids)})
            conn.commit()
            print(f"  Successfully cleaned up data for {fid}.")
