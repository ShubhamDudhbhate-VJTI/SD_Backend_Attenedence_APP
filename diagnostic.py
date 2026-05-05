
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Integer, DateTime, ForeignKey, Boolean, Numeric, Text, func
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

def run_diagnostic():
    print("--- DIAGNOSTIC START ---")
    hod_username = "241080017"
    hod = db.query(User).filter(User.username == hod_username).first()
    if not hod:
        print(f"Error: User {hod_username} not found")
        # Create it properly
        hod = User(id=str(uuid.uuid4()), username=hod_username, full_name="HOD Shubham", role="faculty")
        db.add(hod)
        db.commit()
        print(f"Created HOD user: {hod.id}")
    else:
        print(f"HOD found: {hod.id} ({hod.username})")

    hod_teacher = db.query(Teacher).filter(Teacher.id == hod.id).first()
    if not hod_teacher:
        print("Error: Teacher record for HOD not found")
        hod_teacher = Teacher(id=hod.id, full_name=hod.full_name, department_id="IT", branch="IT")
        db.add(hod_teacher)
        db.commit()
    else:
        print(f"HOD Teacher record: dept={hod_teacher.department_id}, branch={hod_teacher.branch}")

    fac_username = "VBNIKAM"
    fac = db.query(User).filter(User.username == fac_username).first()
    if not fac:
        print(f"Creating Faculty {fac_username}")
        fac = User(id="VBNIKAM", username=fac_username, full_name="Prof. V. B. Nikam", role="faculty")
        db.add(fac)
        db.commit()

    # Ensure faculty has Teacher record
    if not db.query(Teacher).filter(Teacher.id == fac.id).first():
        db.add(Teacher(id=fac.id, full_name=fac.full_name, department_id="IT", branch="IT"))
        db.commit()

    # Create test subject
    sub = db.query(Subject).filter(Subject.name == "System Design").first()
    if not sub:
        sub = Subject(id=str(uuid.uuid4()), name="System Design", branch="IT", year="Second Year", department_id="IT")
        db.add(sub)
        db.commit()
    print(f"Subject: {sub.name}, ID: {sub.id}")

    # Create sessions for the target date range
    target_start = datetime(2026, 4, 30)
    target_end = datetime(2026, 5, 30)

    # Create 5 sessions within range
    for i in range(5):
        s_time = target_start + timedelta(days=i+1, hours=10)
        sess = AttendanceSession(id=str(uuid.uuid4()), subject_id=sub.id, faculty_id=fac.id, start_time=s_time, status="completed")
        db.add(sess)
        db.commit()

        # Add students
        for j in range(3):
            reg = f"STUD_IT_{j}"
            stu_user = db.query(User).filter(User.username == reg).first()
            if not stu_user:
                stu_user = User(id=str(uuid.uuid4()), username=reg, full_name=f"Student {reg}", role="student")
                db.add(stu_user)
                db.commit()

            stu = db.query(Student).filter(Student.id == stu_user.id).first()
            if not stu:
                stu = Student(id=stu_user.id, registration_number=reg, full_name=stu_user.full_name, branch="IT", year="Second Year")
                db.add(stu)
                db.commit()

            # Record
            rec = AttendanceRecord(id=str(uuid.uuid4()), session_id=sess.id, student_id=stu_user.id, status="present")
            db.add(rec)
            db.commit()

    print("--- SIMULATING BACKEND QUERY ---")
    did = "IT"
    faculty_id = "VBNIKAM"
    branch = "IT"
    year = "Second Year"
    sd_str = "2026-04-30"
    ed_str = "2026-05-30"

    actual_dept = did
    query = db.query(AttendanceSession, Subject, User).join(Subject).outerjoin(User, AttendanceSession.faculty_id == User.id)
    query = query.filter((Subject.department_id.ilike(f"%{actual_dept}%")) | (Subject.branch.ilike(f"%{actual_dept}%")))

    if faculty_id:
        query = query.filter((AttendanceSession.faculty_id == faculty_id) | (User.username.ilike(f"%{faculty_id}%")))
    if branch:
        query = query.filter(Subject.branch.ilike(f"%{branch}%"))
    if year:
        query = query.filter(Subject.year.ilike(f"%{year}%"))

    sd = datetime.strptime(sd_str, '%Y-%m-%d')
    ed = datetime.strptime(ed_str, '%Y-%m-%d') + timedelta(days=1)
    query = query.filter(AttendanceSession.start_time >= sd)
    query = query.filter(AttendanceSession.start_time < ed)

    results = query.all()
    print(f"Found {len(results)} sessions")
    for r in results:
        print(f"Session: {r[0].id}, Time: {r[0].start_time}, Faculty: {r[2].full_name if r[2] else 'None'}")

run_diagnostic()
