
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Integer, DateTime, ForeignKey, Boolean, Numeric, Text, or_
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

engine = create_engine("sqlite:///D:/AndroidProjects/DBMS_Shubham_Application/backend/attendance.db")
Session = sessionmaker(bind=engine)
db = Session()

def debug():
    department_id = "IT"
    faculty_id = "VBNIKAM"
    branch = "IT"
    year = "Second Year"
    subject_id = "aa7b996b-2831-4d48-8cd5-8e2b4064ee95"
    start_date = "2026-04-25"
    end_date = "2026-05-15"

    print(f"DEBUGGING QUERY with params: dept={department_id}, faculty={faculty_id}, branch={branch}, year={year}, subject={subject_id}")

    did = department_id
    teacher_lookup = db.query(Teacher).filter(Teacher.id == did).first()
    actual_dept = teacher_lookup.department_id or teacher_lookup.branch if teacher_lookup else did
    print(f"Resolved actual_dept: {actual_dept}")

    query = db.query(AttendanceSession, Subject, User).join(Subject).outerjoin(User, AttendanceSession.faculty_id == User.id)

    # Check base filter
    base_filter = (Subject.department_id.ilike(f"%{actual_dept}%")) | (Subject.branch.ilike(f"%{actual_dept}%"))
    count_base = query.filter(base_filter).count()
    print(f"Sessions matching dept {actual_dept}: {count_base}")

    if faculty_id and faculty_id != "All":
        fid = faculty_id
        query = query.filter((AttendanceSession.faculty_id == fid) | (User.username.ilike(f"%{fid}%")) | (User.full_name.ilike(f"%{fid}%")))
        print(f"Sessions after faculty filter: {query.count()}")

    if subject_id and subject_id != "All":
        query = query.filter(AttendanceSession.subject_id == subject_id)
        print(f"Sessions after subject filter: {query.count()}")

    if branch and branch != "All":
        query = query.filter(Subject.branch.ilike(f"%{branch}%"))
        print(f"Sessions after branch filter: {query.count()}")

    if year and year != "All":
        y_val = year.lower()
        if "second" in y_val or "se" in y_val: y_patterns = ["%Second%", "%SE%", "%2nd%"]
        else: y_patterns = [f"%{year}%"]
        query = query.filter(or_(*[Subject.year.ilike(p) for p in y_patterns]))
        print(f"Sessions after year filter: {query.count()}")

    if start_date:
        sd = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(AttendanceSession.start_time >= sd)
    if end_date:
        ed = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(AttendanceSession.start_time < ed)

    print(f"Final session count: {query.count()}")

    if query.count() == 0:
        # Check if subject even exists
        sub = db.query(Subject).filter(Subject.id == subject_id).first()
        if sub:
            print(f"Subject FOUND: {sub.name}, branch={sub.branch}, year={sub.year}, dept={sub.department_id}")
            # Check sessions for this subject
            sess_count = db.query(AttendanceSession).filter(AttendanceSession.subject_id == subject_id).count()
            print(f"Total sessions for this subject ID: {sess_count}")
        else:
            print("Subject NOT FOUND in database")

debug()
