
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
    username = "241080017"
    # User might be logged in with a UUID but identify as this username
    # Let's create/update the user entry
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user_id = str(uuid.uuid4())
        user = User(id=user_id, username=username, full_name="HOD User 241080017", role="faculty")
        db.add(user)
        db.flush()
    else:
        user_id = user.id
        user.role = "faculty"

    # Make sure they are a Teacher/HOD
    teacher = db.query(Teacher).filter(Teacher.id == user_id).first()
    if not teacher:
        teacher = Teacher(id=user_id, employee_id=f"EMP_{username}", full_name="HOD User 241080017", department_id="IT", branch="IT")
        db.add(teacher)
    else:
        teacher.department_id = "IT"
        teacher.branch = "IT"

    # Now create some data they can actually see (Subject in IT, Year Second Year)
    sub_name = "Cloud Computing"
    subject = db.query(Subject).filter(Subject.name == sub_name, Subject.branch == "IT").first()
    if not subject:
        subject = Subject(id=str(uuid.uuid4()), name=sub_name, branch="IT", year="Second Year", department_id="IT")
        db.add(subject)
        db.flush()

    # Create a session for this faculty
    session_time = datetime.now() - timedelta(days=2) # 2 days ago
    session = AttendanceSession(id=str(uuid.uuid4()), subject_id=subject.id, faculty_id=user_id, start_time=session_time, status="completed")
    db.add(session)
    db.flush()

    # Create a student and record
    student_uid = str(uuid.uuid4())
    student_user = User(id=student_uid, username=f"stud_{username}", full_name="Sample Student", role="student")
    student = Student(id=student_uid, registration_number="REG_TEST_101", full_name="Sample Student", branch="IT", year="Second Year")
    db.add(student_user)
    db.add(student)
    db.flush()

    record = AttendanceRecord(id=str(uuid.uuid4()), session_id=session.id, student_id=student_uid, status="present")
    db.add(record)

    db.commit()
    print(f"Successfully configured user {username} as HOD of IT with sample data.")
except Exception as e:
    db.rollback()
    print(f"Error: {e}")
finally:
    db.close()
