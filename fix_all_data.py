
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Integer, DateTime, ForeignKey, Boolean, Numeric, Text
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

# Minimal models for fix script
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

engine = create_engine("sqlite:///D:/AndroidProjects/DBMS_Shubham_Application/backend/attendance.db")
Session = sessionmaker(bind=engine)
db = Session()

try:
    # 1. Ensure User 241080017 is an HOD of "IT"
    hod_username = "241080017"
    hod = db.query(User).filter(User.username == hod_username).first()
    if not hod:
        hod = User(id=str(uuid.uuid4()), username=hod_username, full_name="HOD Shubham", role="faculty")
        db.add(hod)
        db.flush()

    hod_teacher = db.query(Teacher).filter(Teacher.id == hod.id).first()
    if not hod_teacher:
        hod_teacher = Teacher(id=hod.id, full_name=hod.full_name, department_id="IT", branch="IT")
        db.add(hod_teacher)
    else:
        hod_teacher.department_id = "IT"
        hod_teacher.branch = "IT"

    # 2. Ensure Faculty VBNIKAM exists
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

    # 3. Create the EXACT Subject ID your app is requesting
    target_subject_id = "aa7b996b-2831-4d48-8cd5-8e2b4064ee95"

    # Delete if exists to refresh
    db.query(AttendanceRecord).filter(AttendanceRecord.session_id.in_(
        db.query(AttendanceSession.id).filter(AttendanceSession.subject_id == target_subject_id)
    )).delete(synchronize_session=False)
    db.query(AttendanceSession).filter(AttendanceSession.subject_id == target_subject_id).delete(synchronize_session=False)
    db.query(Subject).filter(Subject.id == target_subject_id).delete(synchronize_session=False)

    subject = Subject(id=target_subject_id, name="Mobile Development (TEST)", branch="IT", year="Second Year", department_id="IT")
    db.add(subject)
    db.flush()

    # 4. Create Sessions for VBNIKAM on this subject
    # Range: April 25 to May 15, 2026
    start_date = datetime(2026, 4, 25)
    for i in range(15):
        s_time = start_date + timedelta(days=i, hours=11)
        session = AttendanceSession(id=str(uuid.uuid4()), subject_id=target_subject_id, faculty_id=fac.id, start_time=s_time, status="completed")
        db.add(session)
        db.flush()

        # Create 10 students and attendance for each session
        for j in range(10):
            reg = f"241080_{j}"
            stu_user = db.query(User).filter(User.username == reg).first()
            if not stu_user:
                stu_user = User(id=str(uuid.uuid4()), username=reg, full_name=f"IT Student {j}", role="student")
                db.add(stu_user)
                db.flush()

            stu = db.query(Student).filter(Student.id == stu_user.id).first()
            if not stu:
                stu = Student(id=stu_user.id, registration_number=reg, full_name=stu_user.full_name, branch="IT", year="Second Year", department_id="IT")
                db.add(stu)

            # 90% attendance
            if (i + j) % 10 != 0:
                rec = AttendanceRecord(id=str(uuid.uuid4()), session_id=session.id, student_id=stu_user.id, status="present")
                db.add(rec)

    db.commit()
    print(f"SUCCESS: Database fully synced for Subject ID: {target_subject_id}")
    print("Faculty: Prof. V. B. Nikam, Branch: IT, Year: Second Year.")
except Exception as e:
    db.rollback()
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
