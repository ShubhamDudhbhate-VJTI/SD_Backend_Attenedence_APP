
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import sessionmaker, declarative_base

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

db_paths = [
    "sqlite:///D:/AndroidProjects/DBMS_Shubham_Application/attendance.db",
    "sqlite:///D:/AndroidProjects/DBMS_Shubham_Application/backend/attendance.db"
]

target_subject_id = "aa7b996b-2831-4d48-8cd5-8e2b4064ee95"

for path in db_paths:
    print(f"Syncing database: {path}")
    engine = create_engine(path)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        # 1. Setup HOD
        hod_user = db.query(User).filter(User.username == "241080017").first()
        if not hod_user:
            hod_user = User(id=str(uuid.uuid4()), username="241080017", full_name="Shubham HOD", role="faculty")
            db.add(hod_user)
            db.flush()

        if not db.query(Teacher).filter(Teacher.id == hod_user.id).first():
            db.add(Teacher(id=hod_user.id, full_name=hod_user.full_name, department_id="IT", branch="IT"))

        # 2. Setup Faculty
        fac = db.query(User).filter(User.username == "VBNIKAM").first()
        if not fac:
            fac = User(id="VBNIKAM", username="VBNIKAM", full_name="Prof. V. B. Nikam", role="faculty")
            db.add(fac)
            db.flush()

        if not db.query(Teacher).filter(Teacher.id == fac.id).first():
            db.add(Teacher(id=fac.id, full_name=fac.full_name, department_id="IT", branch="IT"))

        # 3. Setup Subject (The one from your logs)
        sub = db.query(Subject).filter(Subject.id == target_subject_id).first()
        if not sub:
            sub = Subject(id=target_subject_id, name="Mobile Development (Sync)", branch="IT", year="Second Year", department_id="IT")
            db.add(sub)
        else:
            sub.branch = "IT"
            sub.year = "Second Year"
            sub.department_id = "IT"
        db.flush()

        # 4. Create Sessions (April 25 - May 15)
        db.query(AttendanceSession).filter(AttendanceSession.subject_id == target_subject_id).delete()
        start_date = datetime(2026, 4, 25)
        for i in range(15):
            s_time = start_date + timedelta(days=i, hours=10)
            sess = AttendanceSession(id=str(uuid.uuid4()), subject_id=target_subject_id, faculty_id=fac.id, start_time=s_time, status="completed")
            db.add(sess)
            db.flush()

            # Add a student and record
            stu_reg = f"SYNC_STU_{i}"
            stu = db.query(Student).filter(Student.registration_number == stu_reg).first()
            if not stu:
                stu_user = User(id=str(uuid.uuid4()), username=stu_reg, full_name=f"Student {i}", role="student")
                db.add(stu_user)
                db.flush()
                stu = Student(id=stu_user.id, registration_number=stu_reg, full_name=stu_user.full_name, branch="IT", year="Second Year", department_id="IT")
                db.add(stu)
                db.flush()

            db.add(AttendanceRecord(id=str(uuid.uuid4()), session_id=sess.id, student_id=stu.id, status="present"))

        db.commit()
        print(f"Done syncing {path}")
    except Exception as e:
        print(f"Error syncing {path}: {e}")
        db.rollback()
    finally:
        db.close()
