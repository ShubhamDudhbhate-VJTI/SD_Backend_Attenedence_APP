
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
    # 1. Setup User 241080017 as HOD
    username = "241080017"
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(id=str(uuid.uuid4()), username=username, full_name="Shubham HOD", role="faculty")
        db.add(user)
        db.flush()

    teacher = db.query(Teacher).filter(Teacher.id == user.id).first()
    if not teacher:
        teacher = Teacher(id=user.id, employee_id=f"EMP_{username}", full_name=user.full_name, department_id="IT", branch="IT")
        db.add(teacher)
    else:
        teacher.department_id = "IT"
        teacher.branch = "IT"

    # 2. Setup VBNIKAM as Faculty
    fac_username = "VBNIKAM"
    fac_user = db.query(User).filter(User.username == fac_username).first()
    if not fac_user:
        fac_user = User(id="VBNIKAM", username=fac_username, full_name="Prof. V. B. Nikam", role="faculty")
        db.add(fac_user)
        db.flush()

    fac_teacher = db.query(Teacher).filter(Teacher.id == fac_user.id).first()
    if not fac_teacher:
        fac_teacher = Teacher(id=fac_user.id, employee_id="EMP_VB", full_name="Prof. V. B. Nikam", department_id="IT", branch="IT")
        db.add(fac_teacher)

    # 3. Create a Subject that matches the filter "Second Year" and "IT"
    sub_name = "Mobile Application Development"
    subject = db.query(Subject).filter(Subject.name == sub_name).first()
    if not subject:
        subject = Subject(id=str(uuid.uuid4()), name=sub_name, branch="IT", year="Second Year", department_id="IT")
        db.add(subject)
        db.flush()

    # 4. Create Sessions for TODAY so they don't need to change date filters much
    today = datetime.now()
    for i in range(5):
        s_time = today - timedelta(days=i, hours=2)
        session = AttendanceSession(id=str(uuid.uuid4()), subject_id=subject.id, faculty_id=fac_user.id, start_time=s_time, status="completed")
        db.add(session)
        db.flush()

        # Create 10 students for each session
        for j in range(10):
            reg = f"241080{i}{j:02d}"
            stu_user = db.query(User).filter(User.username == reg).first()
            if not stu_user:
                stu_user = User(id=str(uuid.uuid4()), username=reg, full_name=f"Student {reg}", role="student")
                db.add(stu_user)
                db.flush()

            stu = db.query(Student).filter(Student.id == stu_user.id).first()
            if not stu:
                stu = Student(id=stu_user.id, registration_number=reg, full_name=stu_user.full_name, branch="IT", year="Second Year")
                db.add(stu)

            # Mark attendance for some students to create variance
            if (i + j) % 3 != 0:
                rec = AttendanceRecord(id=str(uuid.uuid4()), session_id=session.id, student_id=stu_user.id, status="present")
                db.add(rec)

    db.commit()
    print(f"Demo data successfully injected for HOD {username}")
    print(f"Now search for Faculty: Prof. V. B. Nikam, Branch: IT, Year: Second Year")
except Exception as e:
    db.rollback()
    import traceback
    traceback.print_exc()
finally:
    db.close()
