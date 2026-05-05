
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Integer, DateTime, ForeignKey, Boolean, Numeric, Text, or_, func
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "app_users"
    id = Column(String, primary_key=True)
    username = Column(String, unique=True)
    full_name = Column(String)

class Teacher(Base):
    __tablename__ = "app_teachers"
    id = Column(String, ForeignKey("app_users.id"), primary_key=True)
    department_id = Column(String)
    branch = Column(String)

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

# Test both DBs
db_paths = [
    "sqlite:///D:/AndroidProjects/DBMS_Shubham_Application/attendance.db",
    "sqlite:///D:/AndroidProjects/DBMS_Shubham_Application/backend/attendance.db"
]

def is_valid(val): return val and val not in ["All", "null", "None", "undefined"]

def simulate(db_url):
    print(f"\nSIMULATING ON: {db_url}")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Exact params from logs
    department_id = "IT"
    faculty_id = "VBNIKAM"
    branch = "IT"
    year = "Second Year"
    start_date = "2026-04-25"
    end_date = "2026-05-15"

    did = department_id
    teacher_lookup = db.query(Teacher).filter(Teacher.id == did).first()
    actual_dept = teacher_lookup.department_id or teacher_lookup.branch if teacher_lookup else did
    print(f"Resolved actual_dept: {actual_dept}")

    query = db.query(AttendanceSession, Subject, User).join(Subject).outerjoin(User, AttendanceSession.faculty_id == User.id)
    query = query.filter((Subject.department_id.ilike(f"%{actual_dept}%")) | (Subject.branch.ilike(f"%{actual_dept}%")))

    if is_valid(faculty_id):
        fid = faculty_id
        query = query.filter((AttendanceSession.faculty_id == fid) | (User.username.ilike(f"%{fid}%")) | (User.full_name.ilike(f"%{fid}%")))

    if is_valid(branch):
        query = query.filter(Subject.branch.ilike(f"%{branch}%"))

    if is_valid(year):
        y_val = year.lower()
        if "second" in y_val or "se" in y_val: y_patterns = ["%Second%", "%SE%", "%2nd%"]
        else: y_patterns = [f"%{year}%"]
        query = query.filter(or_(*[Subject.year.ilike(p) for p in y_patterns]))

    if start_date:
        sd = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(AttendanceSession.start_time >= sd)
    if end_date:
        ed = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(AttendanceSession.start_time < ed)

    sessions = query.all()
    print(f"Sessions found: {len(sessions)}")

    if not sessions:
        print("RESULT: 404 - No sessions found")
        return

    session_ids = [s[0].id for s in sessions]

    # Student query
    student_query = db.query(Student).filter((Student.department_id.ilike(f"%{actual_dept}%")) | (Student.branch.ilike(f"%{actual_dept}%")))
    if is_valid(branch):
        student_query = student_query.filter(Student.branch.ilike(f"%{branch}%"))
    if is_valid(year):
        y_val = year.lower()
        if "second" in y_val or "se" in y_val: y_patterns = ["%Second%", "%SE%", "%2nd%"]
        else: y_patterns = [f"%{year}%"]
        student_query = student_query.filter(or_(*[Student.year.ilike(p) for p in y_patterns]))

    dept_student_ids = [s.id for s in student_query.all()]
    print(f"Dept students found: {len(dept_student_ids)}")

    attended_student_ids = [r[0] for r in db.query(AttendanceRecord.student_id).filter(AttendanceRecord.session_id.in_(session_ids)).distinct().all()]
    print(f"Attended students found: {len(attended_student_ids)}")

    target_student_ids = list(set(dept_student_ids + attended_student_ids))
    print(f"Target student IDs: {len(target_student_ids)}")

    if not target_student_ids:
        print("RESULT: 404 - No students found")
    else:
        print("RESULT: 200 - SUCCESS")

for path in db_paths:
    simulate(path)
