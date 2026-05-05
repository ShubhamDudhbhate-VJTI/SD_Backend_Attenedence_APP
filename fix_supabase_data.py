
import os
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Integer, DateTime, ForeignKey, Boolean, Numeric, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
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
        print("DATABASE_URL not found in .env")
        return

    db_url = db_url.replace("postgres://", "postgresql://", 1)
    print(f"Connecting to: {db_url.split('@')[-1]}") # Print host only for security

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # 1. Ensure HOD User 241080017
        hod_username = "241080017"
        hod = db.query(User).filter(User.username == hod_username).first()
        if not hod:
            hod = User(id=str(uuid.uuid4()), username=hod_username, full_name="Shubham HOD", role="faculty")
            db.add(hod)
            db.flush()

        hod_teacher = db.query(Teacher).filter(Teacher.id == hod.id).first()
        if not hod_teacher:
            hod_teacher = Teacher(id=hod.id, full_name=hod.full_name, department_id="IT", branch="IT")
            db.add(hod_teacher)
        else:
            hod_teacher.department_id = "IT"
            hod_teacher.branch = "IT"

        # 2. Ensure Faculty VBNIKAM
        fac_username = "VBNIKAM"
        fac = db.query(User).filter(User.username == fac_username).first()
        if not fac:
            fac = User(id="VBNIKAM", username=fac_username, full_name="Prof. V. B. Nikam", role="faculty")
            db.add(fac)
            db.flush()

        fac_teacher = db.query(Teacher).filter(Teacher.id == fac.id).first()
        if not fac_teacher:
            fac_teacher = Teacher(id=fac.id, full_name="Prof. V. B. Nikam", department_id="IT", branch="IT")
            db.add(fac_teacher)

        # 3. Setup Subject
        # The logs showed the app is specifically looking for 'IT' and 'Second Year'
        target_subject_id = "aa7b996b-2831-4d48-8cd5-8e2b4064ee95"
        subject = db.query(Subject).filter(Subject.id == target_subject_id).first()
        if not subject:
            subject = Subject(id=target_subject_id, name="Mobile Development (Cloud Sync)", branch="IT", year="Second Year", department_id="IT")
            db.add(subject)
        else:
            subject.branch = "IT"
            subject.year = "Second Year"
            subject.department_id = "IT"
        db.flush()

        # 4. Clean old test sessions for this subject to avoid bloat
        # (Be careful not to delete real data if this was a production DB, but this is a dev DB)
        # db.query(AttendanceSession).filter(AttendanceSession.subject_id == target_subject_id).delete(synchronize_session=False)

        # 5. Create Sessions (April 25 - May 15, 2026)
        start_date = datetime(2026, 4, 25)
        for i in range(10):
            s_time = start_date + timedelta(days=i, hours=10)

            # Check if session already exists for this time/subject/faculty to avoid duplicates
            existing_session = db.query(AttendanceSession).filter(
                AttendanceSession.subject_id == target_subject_id,
                AttendanceSession.start_time == s_time
            ).first()

            if not existing_session:
                sess_id = str(uuid.uuid4())
                sess = AttendanceSession(id=sess_id, subject_id=target_subject_id, faculty_id=fac.id, start_time=s_time, status="completed")
                db.add(sess)
                db.flush()

                # Add 5 students and records
                for j in range(5):
                    reg = f"STUD_CLOUD_{j}"
                    stu_user = db.query(User).filter(User.username == reg).first()
                    if not stu_user:
                        stu_user = User(id=str(uuid.uuid4()), username=reg, full_name=f"Cloud Student {j}", role="student")
                        db.add(stu_user)
                        db.flush()

                    stu = db.query(Student).filter(Student.id == stu_user.id).first()
                    if not stu:
                        stu = Student(id=stu_user.id, registration_number=reg, full_name=stu_user.full_name, branch="IT", year="Second Year", department_id="IT")
                        db.add(stu)
                        db.flush()

                    db.add(AttendanceRecord(id=str(uuid.uuid4()), session_id=sess_id, student_id=stu.id, status="present", face_verified=True))

        db.commit()
        print("SUCCESS: Supabase Cloud Database fully synced.")
    except Exception as e:
        db.rollback()
        print(f"FAILED: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    sync_data()
