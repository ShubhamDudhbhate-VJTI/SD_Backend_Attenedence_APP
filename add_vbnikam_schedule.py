import os
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import User, Teacher, Subject, Classroom, Schedule, Base, DATABASE_URL

# Connect to database
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def add_dummy_schedule():
    # 1. Find the faculty user
    user = db.query(User).filter(User.username == "vbnikam").first()
    if not user:
        print("User 'vbnikam' not found!")
        return

    faculty_id = user.id
    print(f"Found faculty: {user.full_name} (ID: {faculty_id})")

    # 2. Get some subjects and a classroom
    subjects = db.query(Subject).limit(5).all()
    classroom = db.query(Classroom).first()

    if not subjects or not classroom:
        print("Need at least one subject and one classroom in the database!")
        return

    # 3. Define the week days
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    # 4. Clear existing dummy schedule for this user to avoid duplicates if re-run
    # (Optional, but good for testing)
    # db.query(Schedule).filter(Schedule.faculty_id == faculty_id).delete()

    # 5. Add schedule records
    # 9 AM to 5 PM is 8 hours. Let's add 4 slots of 2 hours each or something similar.
    # Or just one big slot for testing? User said 9 to 5.

    count = 0
    for i, day in enumerate(days):
        # Rotate subjects for variety
        subject = subjects[i % len(subjects)]

        # Example schedule:
        # Slot 1: 09:00 - 11:00
        # Slot 2: 11:00 - 13:00
        # Slot 3: 14:00 - 16:00
        # Slot 4: 16:00 - 17:00

        slots = [
            ("09:00", "11:00"),
            ("11:00", "13:00"),
            ("14:00", "16:00"),
            ("16:00", "17:00")
        ]

        for start, end in slots:
            new_sched = Schedule(
                id=str(uuid.uuid4()),
                subject_id=subject.id,
                classroom_id=classroom.id,
                faculty_id=faculty_id,
                day_of_week=day,
                start_time=start,
                end_time=end,
                is_official=True
            )
            db.add(new_sched)
            count += 1

    try:
        db.commit()
        print(f"Successfully added {count} schedule slots for {user.full_name} for the whole week.")
    except Exception as e:
        db.rollback()
        print(f"Error adding schedule: {e}")

if __name__ == "__main__":
    add_dummy_schedule()
