
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Integer, DateTime, ForeignKey, Boolean, Numeric, Text
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "app_users"
    id = Column(String, primary_key=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    password_hash = Column(Text)
    full_name = Column(String)
    role = Column(String)

class Teacher(Base):
    __tablename__ = "app_teachers"
    id = Column(String, ForeignKey("app_users.id"), primary_key=True)
    employee_id = Column(String, unique=True)
    full_name = Column(String)
    department_id = Column(String)
    branch = Column(String)

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

try:
    # 1. Create Faculty
    faculty_id = "VBNIKAM"
    if not db.query(User).filter(User.id == faculty_id).first():
        user = User(id=faculty_id, username="VBNIKAM", full_name="Prof. V. B. Nikam", role="faculty")
        teacher = Teacher(id=faculty_id, employee_id="EMP_IT_001", full_name="Prof. V. B. Nikam", department_id="IT", branch="IT")
        db.add(user)
        db.add(teacher)

    # 2. Create Subject
    subject_id = str(uuid.uuid4())
    subject = Subject(id=subject_id, name="Advanced Database Systems", branch="IT", year="Second Year", department_id="IT")
    db.add(subject)

    # 3. Create Student
    student_uid = str(uuid.uuid4())
    student_user = User(id=student_uid, username="test_student", full_name="Test Student IT", role="student")
    student = Student(id=student_uid, registration_number="REG2026_001", full_name="Test Student IT", branch="IT", year="Second Year")
    db.add(student_user)
    db.add(student)

    # 4. Create Session (in May 2026 as per user logs)
    session_id = str(uuid.uuid4())
    session_time = datetime(2026, 5, 1, 10, 0, 0)
    session = AttendanceSession(id=session_id, subject_id=subject_id, faculty_id=faculty_id, start_time=session_time, status="completed")
    db.add(session)

    # 5. Create Attendance Record
    record = AttendanceRecord(id=str(uuid.uuid4()), session_id=session_id, student_id=student_uid, status="present")
    db.add(record)

    db.commit()
    print("Test data successfully injected for IT / Second Year / VBNIKAM")
except Exception as e:
    db.rollback()
    print(f"Error: {e}")
finally:
    db.close()
