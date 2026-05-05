
import os
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Integer, DateTime, ForeignKey, Boolean, Numeric, Text, or_
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class User(Base):
    __tablename__ = "app_users"
    id = Column(String, primary_key=True)
    username = Column(String, unique=True)
    full_name = Column(String)
    role = Column(String)

class Teacher(Base):
    __tablename__ = "app_teachers"
    id = Column(String, ForeignKey("app_users.id"), primary_key=True)
    department_id = Column(String)
    branch = Column(String)
    full_name = Column(String)

class Student(Base):
    __tablename__ = "app_students"
    id = Column(String, ForeignKey("app_users.id"), primary_key=True)
    registration_number = Column(String, unique=True)
    full_name = Column(String)
    branch = Column(String)
    year = Column(String)
    department_id = Column(String)

class Subject(Base):
    __tablename__ = "subjects"
    id = Column(String, primary_key=True)
    name = Column(String)
    branch = Column(String)
    year = Column(String)
    department_id = Column(String)

class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"
    id = Column(String, primary_key=True)
    subject_id = Column(String, ForeignKey("subjects.id"))
    faculty_id = Column(String, ForeignKey("app_users.id"))
    start_time = Column(DateTime)
    status = Column(String)

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("attendance_sessions.id"))
    student_id = Column(String, ForeignKey("app_students.id"))
    status = Column(String)
    face_verified = Column(Boolean, default=False)

def sync_data():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found")
        return

    db_url = db_url.replace("postgres://", "postgresql://", 1)
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # 1. HOD User 241080017
        hod = db.query(User).filter(or_(User.username == "241080017", User.full_name == "Shubham HOD")).first()
        if not hod:
            hod = User(id=str(uuid.uuid4()), username="241080017", full_name="Shubham HOD", role="faculty")
            db.add(hod)
            db.flush()
        else:
            print(f"HOD {hod.username} exists with ID {hod.id}")

        teacher = db.query(Teacher).filter(Teacher.id == hod.id).first()
        if not teacher:
            db.add(Teacher(id=hod.id, full_name=hod.full_name, department_id="IT", branch="IT"))
        else:
            teacher.department_id = "IT"
            teacher.branch = "IT"

        # 2. Faculty VBNIKAM
        # Use ID check first since the error was on pkey (ID)
        fac = db.query(User).filter(User.id == "VBNIKAM").first()
        if not fac:
            # Check by username if ID is different
            fac = db.query(User).filter(User.username == "VBNIKAM").first()

        if not fac:
            fac = User(id="VBNIKAM", username="VBNIKAM", full_name="Prof. V. B. Nikam", role="faculty")
            db.add(fac)
            db.flush()
        else:
            print(f"Faculty exists: {fac.full_name} ({fac.username})")
            fac.role = "faculty"

        fac_teacher = db.query(Teacher).filter(Teacher.id == fac.id).first()
        if not fac_teacher:
            db.add(Teacher(id=fac.id, full_name=fac.full_name, department_id="IT", branch="IT"))
        else:
            fac_teacher.department_id = "IT"
            fac_teacher.branch = "IT"

        # 3. Subject ID: aa7b996b-2831-4d48-8cd5-8e2b4064ee95
        sub_id = "aa7b996b-2831-4d48-8cd5-8e2b4064ee95"
        subject = db.query(Subject).filter(Subject.id == sub_id).first()
        if not subject:
            subject = Subject(id=sub_id, name="Cloud Computing (Cloud Sync)", branch="IT", year="Second Year", department_id="IT")
            db.add(subject)
        else:
            subject.branch = "IT"
            subject.year = "Second Year"
            subject.department_id = "IT"
            subject.name = "Cloud Computing (Cloud Sync)"
        db.flush()

        # 4. Sessions & Records
        # Create sessions if they don't exist for the range
        start_date = datetime(2026, 4, 25)
        created_count = 0
        for i in range(10):
            s_time = start_date + timedelta(days=i, hours=10)

            existing = db.query(AttendanceSession).filter(
                AttendanceSession.subject_id == sub_id,
                AttendanceSession.start_time == s_time
            ).first()

            if not existing:
                sess_id = str(uuid.uuid4())
                db.add(AttendanceSession(id=sess_id, subject_id=sub_id, faculty_id=fac.id, start_time=s_time, status="completed"))
                db.flush()

                # Add students
                for j in range(5):
                    reg = f"CLOUD_STU_{i}_{j}"
                    stu = db.query(Student).filter(Student.registration_number == reg).first()
                    if not stu:
                        s_uid = str(uuid.uuid4())
                        db.add(User(id=s_uid, username=reg, full_name=f"Cloud Student {i}_{j}", role="student"))
                        db.flush()
                        stu = Student(id=s_uid, registration_number=reg, full_name=f"Cloud Student {i}_{j}", branch="IT", year="Second Year", department_id="IT")
                        db.add(stu)
                        db.flush()

                    db.add(AttendanceRecord(id=str(uuid.uuid4()), session_id=sess_id, student_id=stu.id, status="present", face_verified=True))
                created_count += 1

        db.commit()
        print(f"SUCCESS: Supabase Cloud Data Synced. Created {created_count} new sessions.")
    except Exception as e:
        db.rollback()
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    sync_data()
