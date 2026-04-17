import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Body, UploadFile, File, Form, Depends, Response
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
import uuid
import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Integer, DateTime, ForeignKey, Boolean, Float, Text, Date, func, Numeric, LargeBinary, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.dialects.postgresql import UUID, BYTEA
import cv2
import numpy as np
from deepface import DeepFace
import tempfile
import json

# Load .env file
load_dotenv()

# --- DATABASE SETUP ---
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def create_db_engine(url):
    if not url or "sqlite" in url:
        return create_engine("sqlite:///./attendance.db", connect_args={"check_same_thread": False})
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"connect_timeout": 5}
    )

# Try connecting to the primary DB
try:
    print(f"--- DATABASE CHECK: Attempting Supabase Connection ---")
    print(f"Target: {DATABASE_URL.split('@')[-1] if DATABASE_URL else 'None'}")
    engine = create_db_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        print("--- SUCCESS: Connected to Supabase PostgreSQL ---")
except Exception as e:
    print(f"--- ERROR: Supabase Connection Failed ---")
    print(f"Details: {str(e)[:200]}...")
    print("--- FALLBACK: Using local SQLite (Data will NOT show in Supabase) ---")
    engine = create_db_engine("sqlite:///./attendance.db")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Migration for SQLite (Adding columns if they don't exist)
def run_migrations(engine):
    if "sqlite" in str(engine.url):
        with engine.begin() as conn:
            # Check classrooms table
            try:
                conn.execute(text("ALTER TABLE classrooms ADD COLUMN wifi_ssid TEXT"))
                print("Added wifi_ssid to classrooms")
            except Exception: pass

            try:
                conn.execute(text("ALTER TABLE classrooms ADD COLUMN wifi_bssid TEXT"))
                print("Added wifi_bssid to classrooms")
            except Exception: pass

            # Check schedules table
            try:
                conn.execute(text("ALTER TABLE schedules ADD COLUMN is_official BOOLEAN DEFAULT 1"))
                print("Added is_official to schedules")
            except Exception: pass

            # Check subjects table
            try:
                conn.execute(text("ALTER TABLE subjects ADD COLUMN department_id TEXT"))
                print("Added department_id to subjects")
            except Exception: pass

            # Check students table
            try:
                conn.execute(text("ALTER TABLE app_students ADD COLUMN face_image BLOB"))
                print("Added face_image to app_students")
            except Exception: pass
            try:
                conn.execute(text("ALTER TABLE app_students ADD COLUMN device_id TEXT"))
                print("Added device_id to app_students")
            except Exception: pass
            try:
                conn.execute(text("ALTER TABLE app_students ADD COLUMN department_id TEXT"))
                print("Added department_id to app_students")
            except Exception: pass

            # Check teachers table
            try:
                conn.execute(text("ALTER TABLE app_teachers ADD COLUMN department_id TEXT"))
                print("Added department_id to app_teachers")
            except Exception: pass
            try:
                conn.execute(text("ALTER TABLE app_teachers ADD COLUMN branch TEXT"))
                print("Added branch to app_teachers")
            except Exception: pass

# Run migrations immediately
run_migrations(engine)

# --- SQL MODELS ---

class User(Base):
    __tablename__ = "app_users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    password_hash = Column(Text)
    full_name = Column(String)
    role = Column(String)

class Student(Base):
    __tablename__ = "app_students"
    id = Column(String, ForeignKey("app_users.id", ondelete="CASCADE"), primary_key=True)
    registration_number = Column(String, unique=True)
    full_name = Column(String)
    branch = Column(String, nullable=True)
    year = Column(String, nullable=True)
    face_embedding = Column(LargeBinary, nullable=True)
    face_image = Column(LargeBinary, nullable=True) # Added for Supabase storage
    device_id = Column(String, nullable=True)
    department_id = Column(String, nullable=True)

class Teacher(Base):
    __tablename__ = "app_teachers"
    id = Column(String, ForeignKey("app_users.id", ondelete="CASCADE"), primary_key=True)
    employee_id = Column(String, unique=True)
    full_name = Column(String)
    department_id = Column(String, nullable=True)
    branch = Column(String, nullable=True)
    designation = Column(String, nullable=True)
    qualification = Column(String, nullable=True)
    specialization = Column(String, nullable=True)
    phone = Column(String, nullable=True)

class Classroom(Base):
    __tablename__ = "classrooms"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    wifi_ssid = Column(String, nullable=True)
    wifi_bssid = Column(String, nullable=True)

class Subject(Base):
    __tablename__ = "subjects"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    code = Column(String, unique=True, nullable=True) # Optional code
    department_id = Column(String, nullable=True)
    branch = Column(String) # For direct branch access
    year = Column(String)   # For year filtering (First Year, Second Year, etc.)

class BranchSubject(Base):
    __tablename__ = "branch_subjects"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    branch = Column(String)
    year = Column(String)
    subject_id = Column(String, ForeignKey("subjects.id"))

class Enrollment(Base):
    """Used ONLY for Minor/Elective subjects where the student branch doesn't match the subject branch"""
    __tablename__ = "enrollments"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id = Column(String, ForeignKey("subjects.id"))
    student_id = Column(String, ForeignKey("app_students.id"))

class FacultySubject(Base):
    __tablename__ = "faculty_subjects"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    faculty_id = Column(String, ForeignKey("app_users.id"))
    subject_id = Column(String, ForeignKey("subjects.id"))

class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id = Column(String, ForeignKey("subjects.id"))
    classroom_id = Column(String, ForeignKey("classrooms.id"))
    faculty_id = Column(String, ForeignKey("app_users.id"))
    day_of_week = Column(String)
    start_time = Column(String)
    end_time = Column(String)
    is_official = Column(Boolean, default=True)

class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id = Column(String, ForeignKey("subjects.id"))
    faculty_id = Column(String, ForeignKey("app_users.id"))
    classroom_id = Column(String, ForeignKey("classrooms.id"))
    status = Column(String, default="active")
    qr_token = Column(Text)
    start_time = Column(DateTime, default=datetime.utcnow)
    qr_expires_at = Column(DateTime)

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("attendance_sessions.id"))
    student_id = Column(String, ForeignKey("app_students.id"))
    status = Column(String, default="present")
    marked_at = Column(DateTime, default=datetime.utcnow)
    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)
    face_verified = Column(Boolean, default=False)
    wifi_bssid_matched = Column(String, nullable=True)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("app_users.id"))
    title = Column(String)
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

def create_notification(db: Session, user_id: str, title: str, message: str):
    try:
        new_notif = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            message=message,
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.add(new_notif)
        db.commit()
    except Exception as e:
        print(f"Error creating notification: {e}")
        db.rollback()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        print(f"Database Session Error: {e}")
        raise e
    finally:
        db.close()

Base.metadata.create_all(engine)
run_migrations(engine)

app = FastAPI(title="AttendX - Professional Backend")

@app.middleware("http")
async def db_session_middleware(request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        print(f"Request Error: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

# --- Pydantic MODELS ---
class StartSessionRequest(BaseModel):
    faculty_id: str
    subject_id: str
    classroom_id: str
    duration_minutes: int = 45

class SessionResponse(BaseModel):
    session_id: str
    qr_token: str
    expires_at: str
    classroom_name: str

class VerifyWifiRequest(BaseModel):
    session_id: str
    bssid: str
    ssid: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

# --- ENDPOINTS ---

# Ensure upload directory exists
FACES_DIR = "static/faces"
os.makedirs(FACES_DIR, exist_ok=True)

@app.post("/attendance/reset-face/{student_id}")
async def reset_face(student_id: str, db: Session = Depends(get_db)):
    sid = clean_id(student_id)
    # Find user
    user = db.query(User).filter((User.id == sid) | (User.username == sid)).first()
    if not user:
        return {"success": False, "message": "User not found"}

    # Update student record
    student = db.query(Student).filter(Student.id == user.id).first()
    if student:
        student.face_embedding = None
        student.face_image = None  # Clear the actual image as well
        db.commit()

        # Also remove local file
        local_file = os.path.join(FACES_DIR, f"{user.username}.jpg")
        if os.path.exists(local_file):
            try:
                os.remove(local_file)
            except:
                pass

        return {"success": True, "message": f"Face data cleared for {user.username}"}
    return {"success": False, "message": "Student profile not found"}

@app.get("/")
async def root():
    return {"status": "online", "schema": "v2_professional"}

@app.post("/auth/login")
async def login(credentials: dict = Body(...), db: Session = Depends(get_db)):
    login_id = credentials.get("username")
    password = credentials.get("password")

    user = db.query(User).filter(
        (User.email == login_id) | (User.username == login_id)
    ).first()

    # NOTE: In production, compare hashed passwords.
    if user and user.password_hash == password:
        return {"success": True, "user_id": str(user.id), "role": user.role, "name": user.full_name}

    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/auth/signup")
async def signup(user_data: dict = Body(...), db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_data.get("email")) | (User.username == user_data.get("username"))
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    # Use provided ID (like FAC_001) or generate a UUID
    new_user_id = str(user_data.get("id") or uuid.uuid4())

    new_user = User(
        id=new_user_id,
        username=user_data.get("username") or user_data.get("email").split('@')[0],
        email=user_data.get("email"),
        password_hash=user_data.get("password"),
        full_name=user_data.get("full_name"),
        role=user_data.get("role")
    )

    db.add(new_user)
    db.flush() # Ensure the user is created before adding the student record

    if user_data.get("role") == "student":
        username = user_data.get("username") or user_data.get("email").split('@')[0]
        new_student = Student(
            id=new_user_id,
            full_name=user_data.get("full_name"),
            registration_number=username,
            branch=user_data.get("branch"),
            year=user_data.get("year")
        )
        db.add(new_student)
    elif user_data.get("role") == "faculty":
        new_teacher = Teacher(
            id=new_user_id,
            full_name=user_data.get("full_name"),
            employee_id=user_data.get("username"),
            branch=user_data.get("branch"),
            designation=user_data.get("designation"),
            qualification=user_data.get("qualification"),
            specialization=user_data.get("specialization"),
            phone=user_data.get("phone")
        )
        db.add(new_teacher)

    db.commit()
    print(f"Successfully created user: {user_data.get('email')} with ID: {new_user_id}")
    return {"success": True, "user_id": new_user_id}

# --- SEED DATA FOR TESTING ---
@app.on_event("startup")
def seed_data():
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            print("--- Seeding Initial Test Data ---")
            # Create a Test Faculty
            fac_id = "FAC001"
            fac_user = User(id=fac_id, username="faculty", email="fac@vjti.ac.in", password_hash="123456", full_name="Dr. VJTI Faculty", role="faculty")
            db.add(fac_user)
            db.add(Teacher(id=fac_id, full_name="Dr. VJTI Faculty", employee_id="FAC001", branch="Information Technology", designation="Professor"))

            # Create a Test Student
            stu_id = "ST001"
            stu_user = User(id=stu_id, username="student", email="stu@vjti.ac.in", password_hash="123456", full_name="Shubham Student", role="student")
            db.add(stu_user)
            db.add(Student(id=stu_id, full_name="Shubham Student", registration_number="ST001", branch="Information Technology", year="Second Year"))

            # Create a Classroom and Subject
            room = Classroom(id="ROOM001", name="Room 101", wifi_bssid="00:11:22:33:44:55")
            sub = Subject(id="SUB001", name="DBMS", code="CS301", branch="Computer Engineering", year="Third Year")
            db.add(room)
            db.add(sub)
            db.commit()
            print("--- Seed Data Created! ---")
            print("Login with: faculty / 123456  OR  student / 123456")
        else:
            print(f"--- Database already has {db.query(User).count()} users. Skipping seed. ---")
    except Exception as e:
        print(f"--- Seeding Error: {e} ---")
    finally:
        db.close()

@app.get("/classrooms")
async def get_classrooms(db: Session = Depends(get_db)):
    rooms = db.query(Classroom).all()
    return [{"id": str(r.id), "name": r.name, "wifi_bssid": r.wifi_bssid} for r in rooms]

@app.get("/subjects")
async def get_subjects(db: Session = Depends(get_db)):
    subjects = db.query(Subject).all()
    return [{"id": str(s.id), "name": s.name, "code": s.code} for s in subjects]

@app.get("/faculty/subjects/{faculty_id}")
async def get_faculty_subjects(faculty_id: str, db: Session = Depends(get_db)):
    """Returns subjects assigned to a teacher via FacultySubject or Schedule"""
    # 1. Get subjects from explicit FacultySubject mapping
    explicit_subjects = db.query(Subject).join(
        FacultySubject, Subject.id == FacultySubject.subject_id
    ).filter(FacultySubject.faculty_id == faculty_id).all()

    # 2. Get subjects from Schedule (backup)
    scheduled_subjects = db.query(Subject).join(
        Schedule, Subject.id == Schedule.subject_id
    ).filter(Schedule.faculty_id == faculty_id).all()

    # Combine and remove duplicates by ID
    all_subjects_dict = {s.id: s for s in (explicit_subjects + scheduled_subjects)}

    # Also fetch branch/year info for these subjects to show in dropdown
    results = []
    for sid, s in all_subjects_dict.items():
        branch_info = db.query(BranchSubject).filter(BranchSubject.subject_id == sid).first()
        results.append({
            "id": str(s.id),
            "name": s.name,
            "code": s.code,
            "branch": branch_info.branch if branch_info else "N/A",
            "year": branch_info.year if branch_info else "N/A"
        })

    return results

@app.get("/student/subjects/{student_id}")
async def get_student_subjects(student_id: str, db: Session = Depends(get_db)):
    """Returns all subjects for a student (Branch subjects + Minors)"""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # 1. Subjects from Branch mapping
    branch_subjects = db.query(Subject).join(
        BranchSubject, Subject.id == BranchSubject.subject_id
    ).filter(
        BranchSubject.branch == student.branch,
        BranchSubject.year == student.year
    ).all()

    # 2. Subjects from Minor Enrollments
    minor_subjects = db.query(Subject).join(
        Enrollment, Subject.id == Enrollment.subject_id
    ).filter(Enrollment.student_id == student_id).all()

    # Combine
    all_subjects = {s.id: s for s in (branch_subjects + minor_subjects)}.values()

    return [{"id": str(s.id), "name": s.name, "code": s.code} for s in all_subjects]

@app.get("/subjects/{subject_id}/students")
async def get_subject_students(subject_id: str, db: Session = Depends(get_db)):
    """Returns all students belonging to the branch/year of the subject + enrolled minors"""
    # 1. Get branches/years linked to this subject
    mappings = db.query(BranchSubject).filter(BranchSubject.subject_id == subject_id).all()

    student_ids = set()

    # 2. Add students from those branches
    for m in mappings:
        branch_students = db.query(Student.id).filter(
            Student.branch == m.branch,
            Student.year == m.year
        ).all()
        for s in branch_students:
            student_ids.add(s[0])

    # 3. Add students from Minor Enrollments
    minor_students = db.query(Enrollment.student_id).filter(Enrollment.subject_id == subject_id).all()
    for s in minor_students:
        student_ids.add(s[0])

    if not student_ids:
        return []

    students = db.query(Student).filter(Student.id.in_(list(student_ids))).all()
    return [{"id": str(s.id), "name": s.full_name, "reg_no": s.registration_number} for s in students]

@app.get("/faculty/reports/{faculty_id}")
async def get_teacher_reports(faculty_id: str, db: Session = Depends(get_db)):
    """Returns a summary of attendance records for subjects taught by this teacher"""
    results = db.query(
        Subject.name,
        Subject.code,
        func.count(AttendanceRecord.id).label("records_count")
    ).join(AttendanceSession, Subject.id == AttendanceSession.subject_id)\
     .join(AttendanceRecord, AttendanceSession.id == AttendanceRecord.session_id)\
     .filter(AttendanceSession.faculty_id == faculty_id)\
     .group_by(Subject.id).all()

    return [
        {"subject_name": name, "subject_code": code, "records_count": count}
        for name, code, count in results
    ]

@app.get("/faculty/schedule/{faculty_id}")
async def get_faculty_schedule(faculty_id: str, day: Optional[str] = None, db: Session = Depends(get_db)):
    fid = clean_id(faculty_id)
    query = db.query(Schedule, Subject, Classroom).join(
        Subject, Schedule.subject_id == Subject.id
    ).join(
        Classroom, Schedule.classroom_id == Classroom.id
    ).filter(Schedule.faculty_id == fid)

    if day:
        query = query.filter(Schedule.day_of_week == day)

    schedule = query.all()

    return [
        {
            "id": str(s.id),
            "day": s.day_of_week,
            "subject": sub.name,
            "subject_id": str(sub.id),
            "subject_code": sub.code,
            "branch": sub.branch,
            "year": sub.year,
            "room": c.name,
            "classroom_id": str(c.id),
            "time": f"{s.start_time} - {s.end_time}",
            "is_official": s.is_official
        }
        for s, sub, c in schedule
    ]

@app.post("/faculty/schedule/{faculty_id}")
async def add_schedule_record(faculty_id: str, record: dict = Body(...), db: Session = Depends(get_db)):
    fid = clean_id(faculty_id)
    # Parse time "09:00 - 10:00"
    time_parts = record.get("time", "09:00 - 10:00").split(" - ")
    start_t = time_parts[0]
    end_t = time_parts[1] if len(time_parts) > 1 else "10:00"

    new_s = Schedule(
        id=str(uuid.uuid4()),
        faculty_id=fid,
        subject_id=record.get("subject_id"),
        classroom_id=record.get("classroom_id"),
        day_of_week=record.get("day"),
        start_time=start_t,
        end_time=end_t,
        is_official=False # Manual additions are not official template
    )
    db.add(new_s)
    db.commit()
    db.refresh(new_s)

    # Return full object for UI
    sub = db.query(Subject).filter(Subject.id == new_s.subject_id).first()
    room = db.query(Classroom).filter(Classroom.id == new_s.classroom_id).first()

    return {
        "id": str(new_s.id),
        "day": new_s.day_of_week,
        "subject": sub.name if sub else "Unknown",
        "subject_id": str(sub.id) if sub else None,
        "room": room.name if room else "Unknown",
        "classroom_id": str(room.id) if room else None,
        "time": f"{new_s.start_time} - {new_s.end_time}",
        "is_official": new_s.is_official
    }

@app.put("/faculty/schedule/{record_id}")
async def update_schedule_record(record_id: str, record: dict = Body(...), db: Session = Depends(get_db)):
    rid = clean_id(record_id)
    s = db.query(Schedule).filter(Schedule.id == rid).first()
    if not s:
        raise HTTPException(status_code=404, detail="Record not found")

    if "subject_id" in record: s.subject_id = record["subject_id"]
    if "classroom_id" in record: s.classroom_id = record["classroom_id"]
    if "day" in record: s.day_of_week = record["day"]

    if "time" in record:
        time_parts = record["time"].split(" - ")
        s.start_time = time_parts[0]
        if len(time_parts) > 1: s.end_time = time_parts[1]

    db.commit()
    return {"success": True}

@app.delete("/faculty/schedule/{record_id}")
async def delete_schedule_record(record_id: str, db: Session = Depends(get_db)):
    rid = clean_id(record_id)
    s = db.query(Schedule).filter(Schedule.id == rid).first()
    if s:
        db.delete(s)
        db.commit()
        return {"success": True}
    raise HTTPException(status_code=404, detail="Record not found")

@app.post("/faculty/schedule/{faculty_id}/sync-official")
async def sync_official_schedule(faculty_id: str, day: Optional[str] = None, db: Session = Depends(get_db)):
    fid = clean_id(faculty_id)
    # If no day is passed, use today's day name (e.g., 'Monday')
    target_day = day or datetime.now().strftime("%A")

    # Fetch records marked as is_official=True for that day
    query = db.query(Schedule, Subject, Classroom).join(
        Subject, Schedule.subject_id == Subject.id
    ).join(
        Classroom, Schedule.classroom_id == Classroom.id
    ).filter(
        Schedule.faculty_id == fid,
        Schedule.is_official == True,
        Schedule.day_of_week == target_day
    )

    official_schedule = query.all()

    # Create the confirmation response
    return {
        "date": datetime.now().strftime("%d %b, %Y"),
        "day": target_day,
        "schedule": [
            {
                "id": str(s.id),
                "day": s.day_of_week,
                "subject": sub.name,
                "subject_id": str(sub.id),
                "subject_code": sub.code,
                "branch": sub.branch,
                "year": sub.year,
                "room": c.name,
                "classroom_id": str(c.id),
                "time": f"{s.start_time} - {s.end_time}",
                "is_official": s.is_official
            }
            for s, sub, c in official_schedule
        ]
    }

@app.get("/student/schedule/{student_id}")
async def get_student_schedule(student_id: str, day: Optional[str] = None, db: Session = Depends(get_db)):
    """Returns the schedule for the student (Branch subjects + Minors)"""
    sid = clean_id(student_id)
    student = db.query(Student).filter(Student.id == sid).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Get subject IDs for this student
    # 1. Branch subjects from BranchSubject mapping table
    branch_sub_ids = [s[0] for s in db.query(BranchSubject.subject_id).filter(
        BranchSubject.branch == student.branch,
        BranchSubject.year == student.year
    ).all()]

    # 2. Subjects that match branch and year directly in the Subject table (Ensures consistency)
    direct_sub_ids = [s[0] for s in db.query(Subject.id).filter(
        Subject.branch == student.branch,
        Subject.year == student.year
    ).all()]

    # 3. Minor subjects from Enrollment table
    minor_sub_ids = [s[0] for s in db.query(Enrollment.subject_id).filter(Enrollment.student_id == sid).all()]

    all_subject_ids = list(set(branch_sub_ids + direct_sub_ids + minor_sub_ids))

    query = db.query(Schedule, Subject, Classroom).join(
        Subject, Schedule.subject_id == Subject.id
    ).join(
        Classroom, Schedule.classroom_id == Classroom.id
    ).filter(
        Schedule.subject_id.in_(all_subject_ids)
    )

    if day:
        query = query.filter(Schedule.day_of_week == day)

    results = query.all()

    return [
        {
            "day": s.day_of_week,
            "subject": sub.name,
            "subject_id": str(sub.id),
            "subject_code": sub.code,
            "branch": sub.branch,
            "year": sub.year,
            "room": c.name,
            "classroom_id": str(c.id),
            "time": f"{s.start_time} - {s.end_time}",
            "is_official": s.is_official
        }
        for s, sub, c in results
    ]

@app.get("/notifications/{user_id}")
async def get_notifications(user_id: str, db: Session = Depends(get_db)):
    notifications = db.query(Notification).filter(
        Notification.user_id == user_id
    ).order_by(Notification.created_at.desc()).all()

    return [
        {
            "id": str(n.id),
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat()
        }
        for n in notifications
    ]

@app.post("/notifications/read/{notification_id}")
async def mark_notification_read(notification_id: str, db: Session = Depends(get_db)):
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if notif:
        notif.is_read = True
        db.commit()
        return {"success": True}
    raise HTTPException(status_code=404, detail="Notification not found")

@app.post("/sessions/start", response_model=SessionResponse)
async def start_session(req: StartSessionRequest, db: Session = Depends(get_db)):
    classroom = db.query(Classroom).filter(Classroom.id == req.classroom_id).first()
    room_name = classroom.name if classroom else "Unknown Room"

    sid = str(uuid.uuid4())
    qr_token = f"QR_{uuid.uuid4().hex[:8].upper()}"
    expiry = datetime.utcnow() + timedelta(minutes=req.duration_minutes)

    new_session = AttendanceSession(
        id=sid,
        faculty_id=req.faculty_id,
        subject_id=req.subject_id,
        classroom_id=req.classroom_id,
        qr_token=qr_token,
        qr_expires_at=expiry,
        status="active"
    )
    db.add(new_session)

    # Get subject name for notification
    subject_obj = db.query(Subject).filter(Subject.id == req.subject_id).first()
    db.commit()

    # 1. Notify the Faculty
    create_notification(
        db, req.faculty_id,
        "Session Started",
        f"You have started a session for {subject_obj.name} in {room_name}."
    )

    # 2. Notify all students in this branch/year
    # Use ILIKE or case-insensitive matching for more robustness
    target_students = db.query(Student).filter(
        Student.branch.ilike(f"%{subject_obj.branch}%"),
        Student.year.ilike(f"%{subject_obj.year}%")
    ).all()

    for student in target_students:
        create_notification(
            db, student.id,
            "Class Started",
            f"{subject_obj.name} class has started in {room_name}. Mark your attendance!"
        )

    return SessionResponse(
        session_id=sid, qr_token=qr_token, expires_at=expiry.isoformat(),
        classroom_name=room_name
    )

@app.post("/attendance/verify-wifi")
async def verify_wifi(req: VerifyWifiRequest, db: Session = Depends(get_db)):
    # Clean inputs
    clean_sid = req.session_id.replace('"', '').strip()
    print(f"DEBUG: WiFi Verify - Session: {clean_sid}, SSID: {req.ssid}")

    session = db.query(AttendanceSession).filter(AttendanceSession.id == clean_sid).first()
    if not session or session.status != "active":
        # TEMPORARY: If session not found, we might be in a testing state where IDs changed
        print(f"WARNING: Session {clean_sid} not found, but allowing WiFi for testing")
        return {"success": True, "message": "Testing Mode: WiFi Bypass"}

    classroom = db.query(Classroom).filter(Classroom.id == session.classroom_id).first()
    if not classroom:
        return {"success": True, "message": "Classroom not found, allowing for testing"}

    # Enhanced WiFi Verification - Case Insensitive & Clean
    clean_req_ssid = (req.ssid or "").replace("\"", "").strip().lower()
    clean_db_ssid = (classroom.wifi_ssid or "").strip().lower()

    if clean_req_ssid == "phone" or clean_req_ssid == "unknown" or clean_req_ssid == clean_db_ssid:
        return {"success": True, "message": "WiFi Verified"}

    # Still allow if it's for testing
    return {"success": True, "message": "WiFi Allowed (Dev Mode)"}

@app.post("/attendance/verify-qr")
async def verify_qr(req: dict = Body(...), db: Session = Depends(get_db)):
    clean_sid = req.get("session_id", "").replace('"', '').strip()
    token = req.get("token", "").replace('"', '').strip()

    print(f"DEBUG: QR Verify - Session: {clean_sid}, Token: {token}")

    session = db.query(AttendanceSession).filter(AttendanceSession.id == clean_sid).first()
    if session and (session.qr_token == token or token.startswith("QR_")):
        return {"success": True}

    # Fallback for testing: if the token contains the session ID, allow it
    if clean_sid in token:
        return {"success": True}

    return {"success": False, "message": "Invalid QR code"}

@app.get("/faculty/sessions/{faculty_id}")
async def get_faculty_sessions(
    faculty_id: str,
    subject_id: Optional[str] = None,
    classroom_id: Optional[str] = None,
    date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(
        AttendanceSession,
        Subject,
        func.count(AttendanceRecord.id).label("student_count")
    ).join(
        Subject, AttendanceSession.subject_id == Subject.id
    ).outerjoin(
        AttendanceRecord, AttendanceSession.id == AttendanceRecord.session_id
    ).filter(
        AttendanceSession.faculty_id == faculty_id
    )

    if subject_id:
        query = query.filter(AttendanceSession.subject_id == subject_id)
    if classroom_id:
        query = query.filter(AttendanceSession.classroom_id == classroom_id)
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            query = query.filter(func.date(AttendanceSession.start_time) == target_date)
        except:
            pass

    results = query.group_by(AttendanceSession.id, Subject.id).order_by(AttendanceSession.start_time.desc()).all()

    return [
        {
            "session_id": str(s.id),
            "subject_id": str(sub.id),
            "subject_name": sub.name,
            "classroom_id": str(s.classroom_id),
            "status": s.status,
            "student_count": count,
            "start_time": s.start_time.isoformat(),
            "expires_at": s.qr_expires_at.isoformat() if s.qr_expires_at else None
        }
        for s, sub, count in results
    ]

@app.get("/sessions/{session_id}/details")
async def get_session_details(session_id: str, db: Session = Depends(get_db)):
    session = db.query(AttendanceSession).filter(AttendanceSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    subject = db.query(Subject).filter(Subject.id == session.subject_id).first()

    records = db.query(AttendanceRecord, Student).join(
        Student, AttendanceRecord.student_id == Student.id
    ).filter(AttendanceRecord.session_id == session_id).all()

    return {
        "session_id": str(session.id),
        "subject_name": subject.name if subject else "Unknown",
        "start_time": session.start_time.isoformat(),
        "total_students": len(records),
        "students": [
            {
                "student_id": r.student_id,
                "student_name": s.full_name,
                "marked_at": r.marked_at.isoformat(),
                "status": r.status
            }
            for r, s in records
        ]
    }

# Helper to clean IDs from quotes or spaces
def clean_id(val: str) -> str:
    if not val: return val
    return str(val).replace('"', '').replace("'", "").strip()

@app.post("/attendance/verify-face")
async def verify_face(
    student_id: str = Form(...),
    session_id: str = Form(...),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    try:
        # 1. Clean and Resolve IDs
        clean_stud_id = student_id.replace('"', '').replace("'", "").strip()
        clean_sess_id = session_id.replace('"', '').replace("'", "").strip()

        print(f"--- ATTENDANCE ATTEMPT: Student {clean_stud_id} ---")

        # Find User first (by Registration Number or UUID)
        user = db.query(User).filter((User.id == clean_stud_id) | (User.username == clean_stud_id)).first()
        if not user:
            # Auto-create user if missing (for seamless testing)
            user = User(id=clean_stud_id, username=clean_stud_id, full_name=f"Student {clean_stud_id}", role="student", password_hash="123456")
            db.add(user)
            db.commit()
            db.refresh(user)

        # Find Student Profile
        student = db.query(Student).filter(Student.id == user.id).first()
        if not student:
            student = Student(id=user.id, full_name=user.full_name, registration_number=user.username, branch="IT", year="Second Year")
            db.add(student)
            db.commit()
            db.refresh(student)

        # 2. Face Storage & Verification Logic
        is_verified = False
        msg = "Attendance marked!"
        if image:
            image_bytes = await image.read()

            # Temporary file for the current scan
            current_path = os.path.join(tempfile.gettempdir(), f"current_{user.username}_{int(time.time())}.jpg")
            with open(current_path, "wb") as f:
                f.write(image_bytes)

            try:
                if not student.face_embedding:
                    # FIRST TIME: Extract and Store Embedding
                    print(f"--- REGISTRATION: Extracting Face Embedding for {user.username} ---")

                    objs = DeepFace.represent(
                        img_path = current_path,
                        model_name = "VGG-Face",
                        detector_backend = "mtcnn", # Changed from opencv for better detection
                        enforce_detection = True
                    )

                    if objs:
                        embedding = objs[0]["embedding"]
                        # Store as JSON string for compatibility
                        student.face_embedding = json.dumps(embedding).encode('utf-8')

                        # ALWAYS: Store the actual image binary in Supabase and locally
                        student.face_image = image_bytes
                        db.commit()

                        # Save the master face image locally
                        os.makedirs(FACES_DIR, exist_ok=True)
                        master_face_path = os.path.join(FACES_DIR, f"{user.username}.jpg")
                        with open(master_face_path, "wb") as f:
                            f.write(image_bytes)

                        is_verified = True
                        msg = "Face registered and attendance marked!"
                        print(f"+++ REGISTRATION SUCCESS: {user.username} (Saved to Supabase & Local) +++")
                    else:
                        return {"success": False, "message": "Could not detect face for registration."}
                else:
                    # SUBSEQUENT TIMES: Verify Embedding
                    print(f"--- VERIFICATION: Comparing embedding for {user.username} ---")

                    objs = DeepFace.represent(
                        img_path = current_path,
                        model_name = "VGG-Face",
                        detector_backend = "mtcnn", # Changed from opencv for better detection
                        enforce_detection = True
                    )

                    if not objs:
                        raise HTTPException(status_code=400, detail="Could not detect face in current scan.")

                    current_emb = np.array(objs[0]["embedding"])
                    stored_emb = np.array(json.loads(student.face_embedding.decode('utf-8')))

                    # Calculate Cosine Distance using numpy
                    dot_product = np.dot(current_emb, stored_emb)
                    norm_current = np.linalg.norm(current_emb)
                    norm_stored = np.linalg.norm(stored_emb)
                    cosine_similarity = dot_product / (norm_current * norm_stored)
                    dist = 1 - cosine_similarity

                    print(f"DEBUG: Cosine Distance: {dist}")

                    # Threshold for VGG-Face is typically 0.40
                    if dist < 0.40:
                        print(f"+++ MATCH FOUND (Distance: {dist}) +++")
                        is_verified = True
                        msg = "Face verified and attendance marked!"
                    else:
                        print(f"!!! NO MATCH (Distance: {dist}) !!!")
                        # Use 401 Unauthorized for face mismatch to trigger error UI in App
                        raise HTTPException(status_code=401, detail="Face does not match our records!")

            except HTTPException as he:
                raise he
            except Exception as ve:
                print(f"--- Face Error: {str(ve)} ---")
                raise HTTPException(status_code=400, detail=f"Face processing error: {str(ve)}")
            finally:
                if os.path.exists(current_path): os.remove(current_path)
        else:
            raise HTTPException(status_code=400, detail="No face image received")

        # 3. Check Session
        session = db.query(AttendanceSession).filter(AttendanceSession.id == clean_sess_id).first()
        if not session:
            # Fallback to latest active session
            session = db.query(AttendanceSession).filter(AttendanceSession.status == "active").order_by(AttendanceSession.start_time.desc()).first()
            if not session:
                raise HTTPException(status_code=404, detail="No active session found")
            clean_sess_id = session.id

        # 4. Mark Attendance Record
        existing = db.query(AttendanceRecord).filter(
            AttendanceRecord.session_id == clean_sess_id,
            AttendanceRecord.student_id == user.id
        ).first()

        if existing:
            return {"success": True, "message": "Attendance already marked for this session"}

        new_record = AttendanceRecord(
            id=str(uuid.uuid4()),
            session_id=clean_sess_id,
            student_id=user.id,
            status="present",
            face_verified=is_verified,
            marked_at=datetime.utcnow()
        )
        db.add(new_record)
        db.commit()

        # Notify student
        create_notification(
            db, user.id,
            "Attendance Marked",
            f"Your attendance for {session.subject_id} has been recorded as Present."
        )

        print(f"+++ SUCCESS: {user.full_name} marked present +++")
        return {"success": True, "message": msg}

    except HTTPException as he:
        db.rollback()
        raise he # Let FastAPI handle the status code
    except Exception as e:
        db.rollback()
        print(f"!!! CRITICAL ERROR: {str(e)} !!!")
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

@app.get("/sessions/{session_id}/attendance")
async def get_attendance(session_id: str, db: Session = Depends(get_db)):
    # Clean the input session_id from any quotes
    sid = session_id.replace('"', '').replace("'", "").strip()

    # Use outerjoin to include records where student profile might be missing
    results = db.query(AttendanceRecord, Student, User).outerjoin(
        Student, AttendanceRecord.student_id == Student.id
    ).outerjoin(
        User, AttendanceRecord.student_id == User.id
    ).filter(AttendanceRecord.session_id == sid).all()

    attendance_list = []
    for r, s, u in results:
        # Determine name: Try Student table, then User table, then ID
        name = s.full_name if s else (u.full_name if u else f"Student {r.student_id}")

        attendance_list.append({
            "student_id": str(r.student_id),
            "student_name": name,
            "timestamp": r.marked_at.isoformat(),
            "status": r.status,
            "face_verified": r.face_verified
        })

    return {
        "session_id": sid,
        "total_count": len(attendance_list),
        "students": attendance_list
    }

@app.get("/student/attendance/{student_id}")
async def get_student_history(student_id: str, db: Session = Depends(get_db)):
    """Returns all sessions conducted for student's class, marking them as Present or Absent"""
    sid = clean_id(student_id)
    student = db.query(Student).filter(Student.id == sid).first()
    if not student:
        return []

    # 1. Identify all relevant subjects for this student (Branch + Direct + Minors)
    branch_sub_ids = [s[0] for s in db.query(Subject.id).filter(
        Subject.branch == student.branch,
        Subject.year == student.year
    ).all()]

    mapped_sub_ids = [s[0] for s in db.query(BranchSubject.subject_id).filter(
        BranchSubject.branch == student.branch,
        BranchSubject.year == student.year
    ).all()]

    minor_sub_ids = [s[0] for s in db.query(Enrollment.subject_id).filter(Enrollment.student_id == sid).all()]

    all_sub_ids = list(set(branch_sub_ids + mapped_sub_ids + minor_sub_ids))

    # 2. Get all sessions ever conducted for these subjects
    sessions = db.query(AttendanceSession, Subject).join(
        Subject, AttendanceSession.subject_id == Subject.id
    ).filter(
        AttendanceSession.subject_id.in_(all_sub_ids)
    ).order_by(AttendanceSession.start_time.desc()).all()

    # 3. Get actual attendance records for this student
    records = db.query(AttendanceRecord).filter(AttendanceRecord.student_id == sid).all()
    record_map = {r.session_id: r for r in records}

    # 4. Construct a comprehensive history list
    history = []
    for s, sub in sessions:
        record = record_map.get(s.id)
        # Using sub.name for subject_id as the Dashboard uses this field for display text
        history.append({
            "subject_id": sub.name,
            "session_id": str(s.id),
            "timestamp": (record.marked_at if record else s.start_time).isoformat(),
            "status": record.status if record else "absent"
        })

    return history

@app.get("/sessions/active")
async def get_active_sessions(db: Session = Depends(get_db)):
    # Simple list of active sessions for the student dashboard
    active = db.query(AttendanceSession, Subject, Classroom).join(
        Subject, AttendanceSession.subject_id == Subject.id
    ).join(
        Classroom, AttendanceSession.classroom_id == Classroom.id
    ).filter(
        AttendanceSession.status == "active"
    ).all()

    return [
        {
            "session_id": str(s.id),
            "subject_id": str(sub.id),
            "classroom_name": c.name,
            "expires_at": s.qr_expires_at.isoformat()
        }
        for s, sub, c in active
    ]

@app.post("/sessions/stop/{session_id}")
async def stop_session(session_id: str, db: Session = Depends(get_db)):
    sid = session_id.replace('"', '').replace("'", "").strip()
    session = db.query(AttendanceSession, Subject).join(
        Subject, AttendanceSession.subject_id == Subject.id
    ).filter(AttendanceSession.id == sid).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_obj, subject_obj = session
    session_obj.status = "stopped"
    db.commit()

    # Notify Faculty with summary
    report_students = []
    records = db.query(AttendanceRecord, Student, User).outerjoin(
        Student, AttendanceRecord.student_id == Student.id
    ).outerjoin(
        User, AttendanceRecord.student_id == User.id
    ).filter(AttendanceRecord.session_id == sid).all()

    for r, s, u in records:
        name = s.full_name if s else (u.full_name if u else f"Student {r.student_id}")
        reg_no = s.registration_number if s else (u.username if u else r.student_id)
        report_students.append({
            "id": reg_no,
            "name": name,
            "time": r.marked_at.isoformat()
        })

    create_notification(
        db, session_obj.faculty_id,
        "Session Summary",
        f"Session for {subject_obj.name} closed. Total Present: {len(report_students)}."
    )

    return {
        "session_id": sid,
        "total_present": len(report_students),
        "students": report_students,
        "course_id": subject_obj.code or subject_obj.name
    }

@app.get("/auth/me/{user_id}")
async def get_user_profile(user_id: str, db: Session = Depends(get_db)):
    uid = clean_id(user_id)
    # 1. Search by ID or Username
    user = db.query(User).filter((User.id == uid) | (User.username == uid)).first()

    if not user:
        # 2. Fallback: Search in specific role tables if user_id looks like a Registration Number
        student = db.query(Student).filter(Student.registration_number == uid).first()
        if student:
            user = db.query(User).filter(User.id == student.id).first()

        teacher = db.query(Teacher).filter(Teacher.employee_id == uid).first()
        if teacher:
            user = db.query(User).filter(User.id == teacher.id).first()

    if not user:
        raise HTTPException(status_code=404, detail=f"User {uid} not found")

    profile_data = {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "academic": {}
    }

    # Fetch role-specific details
    if user.role == "student":
        student = db.query(Student).filter(Student.id == user.id).first()
        if student:
            profile_data["academic"] = {
                "branch": student.branch or "N/A",
                "year": student.year or "N/A",
                "reg_no": student.registration_number or user.username
            }
    elif user.role == "faculty":
        teacher = db.query(Teacher).filter(Teacher.id == user.id).first()
        if teacher:
            profile_data["academic"] = {
                "branch": teacher.branch or "N/A",
                "designation": teacher.designation or "Faculty",
                "employee_id": teacher.employee_id or user.username
            }

    return profile_data

@app.get("/faces/{student_id}.jpg")
async def get_student_face(student_id: str, db: Session = Depends(get_db)):
    # 1. Check local filesystem first
    local_path = os.path.join(FACES_DIR, f"{student_id}.jpg")
    if os.path.exists(local_path):
        return FileResponse(local_path)

    # 2. If not local, try fetching from Supabase
    student = db.query(Student).filter(Student.registration_number == student_id).first()
    if not student:
        # Try by user ID if reg_number fails
        student = db.query(Student).filter(Student.id == student_id).first()

    if student and student.face_image:
        return Response(content=student.face_image, media_type="image/jpeg")

    raise HTTPException(status_code=404, detail="Face image not found")

@app.post("/notifications/send")
async def send_custom_notification(request: dict = Body(...), db: Session = Depends(get_db)):
    target_type = request.get("target_type") # individual, group, class
    target_id = request.get("target_id", "").strip()
    title = request.get("title")
    message = request.get("message")
    sender_id = request.get("sender_id")

    if not all([target_type, target_id, title, message]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    notifications_sent = 0

    if target_type == "individual":
        # target_id is registration number or user ID
        user = db.query(User).filter((User.username == target_id) | (User.id == target_id)).first()
        if user:
            create_notification(db, user.id, title, message)
            notifications_sent = 1
        else:
            # Try to find by registration number in Student table
            student = db.query(Student).filter(Student.registration_number == target_id).first()
            if student:
                create_notification(db, student.id, title, message)
                notifications_sent = 1
            else:
                raise HTTPException(status_code=404, detail=f"Student {target_id} not found")

    elif target_type == "class":
        # target_id is "branch-year" e.g., "Information Technology-Second Year"
        if "-" in target_id:
            parts = target_id.split("-")
            branch = parts[0].strip()
            year = parts[1].strip()
            students = db.query(Student).filter(
                Student.branch.ilike(f"%{branch}%"),
                Student.year.ilike(f"%{year}%")
            ).all()
        else:
            # Fallback to searching only branch if no hyphen
            students = db.query(Student).filter(Student.branch.ilike(f"%{target_id}%")).all()

        for s in students:
            create_notification(db, s.id, title, message)
            notifications_sent += 1

    elif target_type == "group":
        # target_id is Subject Name or Code
        subject = db.query(Subject).filter(
            (Subject.name.ilike(f"%{target_id}%")) | (Subject.code.ilike(f"%{target_id}%"))
        ).first()

        if subject:
            # Get all students for this subject's branch and year (assuming whole class)
            students = db.query(Student).filter(
                Student.branch == subject.branch,
                Student.year == subject.year
            ).all()

            # Also get minor/elective students
            elective_students = db.query(Student).join(Enrollment, Student.id == Enrollment.student_id).filter(
                Enrollment.subject_id == subject.id
            ).all()

            # Combine unique students
            all_target_students = {s.id: s for s in (students + elective_students)}.values()

            for s in all_target_students:
                create_notification(db, s.id, title, message)
                notifications_sent += 1
        else:
            raise HTTPException(status_code=404, detail=f"Subject {target_id} not found")

    return {"success": True, "sent_to": notifications_sent}

@app.get("/debug/check-setup")
async def check_setup(db: Session = Depends(get_db)):
    """Debug endpoint to see if students and subjects are mapped correctly"""
    student_counts = db.query(Student.branch, Student.year, func.count(Student.id)).group_by(Student.branch, Student.year).all()
    subject_counts = db.query(Subject.branch, Subject.year, func.count(Subject.id)).group_by(Subject.branch, Subject.year).all()

    return {
        "student_distribution": [{"branch": b, "year": y, "count": c} for b, y, c in student_counts],
        "subject_distribution": [{"branch": b, "year": y, "count": c} for b, y, c in subject_counts],
        "total_notifications": db.query(Notification).count()
    }

if __name__ == "__main__":
    # Use 0.0.0.0 to listen on all network interfaces (allows mobile devices to connect)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
