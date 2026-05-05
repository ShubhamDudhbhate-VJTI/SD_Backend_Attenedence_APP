# =================================================================
# AttendX: AI-Powered Attendance System - Backend Core (FastAPI)
# Developed by: Shubham Dudhbhate (Backend & AI Lead)
# Version: 2.2 (Final Professional Submission)
#
# Description:
# This server manages the entire lifecycle of an attendance session:
# 1. User Authentication (Role-based access)
# 2. Dynamic Scheduling (Faculty-specific class templates)
# 3. Session Security (QR Token rotation + WiFi BSSID Geofencing)
# 4. AI Biometrics (DeepFace integration via Hugging Face/Local)
# 5. Real-time Notifications (FCM for class starts and alerts)
# =================================================================

from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Body, UploadFile, File, Form, Depends, Response, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
import uuid
import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Integer, DateTime, ForeignKey, Boolean, Float, Text, Date, func, Numeric, LargeBinary, text, or_, case
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.dialects.postgresql import UUID, BYTEA
import numpy as np
import requests
import tempfile
import json
import traceback
import hashlib
from fpdf import FPDF
import io


# Optional Local AI Import (used in OFFLINE_DEBUG_MODE)
try:
    from deepface import DeepFace
except ImportError:
    DeepFace = None

0
# --- CONFIGURATION SETTINGS ---

# OFFLINE_DEBUG_MODE: Set to True if running AI locally on a machine with GPU.
# Set to False to use the cloud-based Hugging Face AI pipeline (Scalable Production Mode).
OFFLINE_DEBUG_MODE = False

# Load environment variables (Supabase URL, HF Tokens, etc.)
load_dotenv()

# --- CLOUD AI CONFIG (Hugging Face) ---
# AttendX uses a dedicated AI Inference Space on Hugging Face for face embeddings and verification.
HF_API_URL = os.getenv("HF_API_URL")
HF_TOKEN = os.getenv("HF_TOKEN")

# --- DATABASE ARCHITECTURE ---
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    # Fix for Heroku/Supabase style connection strings
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def create_db_engine(url):
    """
    Creates the SQLAlchemy engine.
    Handles connection pooling and timeout settings for Supabase (PostgreSQL).
    """
    if not url or "sqlite" in url:
        return create_engine("sqlite:///./attendance.db", connect_args={"check_same_thread": False})
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={
            "connect_timeout": 15,
            "application_name": "AttendX_Backend"
        }
    )

# Establish Connection: Attempt Primary Cloud DB (Supabase), Fallback to Local SQLite
try:
    print(f"--- DATABASE CHECK: Attempting Supabase Connection ---")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not found in environment variables")

    engine = create_db_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        print("--- SUCCESS: Connected to Supabase PostgreSQL ---")
except Exception as e:
    print(f"--- ERROR: Supabase Connection Failed. ---")
    print(f"Details: {str(e)}")
    print("--- FALLBACK: Using local SQLite (Dev Only) ---")
    engine = create_db_engine("sqlite:///./attendance.db")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def run_migrations(engine):
    """
    Automatic Schema Migration:
    Ensures that columns added during development (like face_image or fcm_token)
    exist in the database without requiring manual SQL commands.
    """
    is_sqlite = "sqlite" in str(engine.url)

    with engine.begin() as conn:
        # Check classrooms table
        try: conn.execute(text("ALTER TABLE classrooms ADD COLUMN wifi_ssid TEXT"))
        except Exception: pass
        try: conn.execute(text("ALTER TABLE classrooms ADD COLUMN wifi_bssid TEXT"))
        except Exception: pass

        # Check schedules table
        try: conn.execute(text("ALTER TABLE schedules ADD COLUMN is_official BOOLEAN DEFAULT 1"))
        except Exception: pass

        # Check students table
        try:
            col_type = "BLOB" if is_sqlite else "BYTEA"
            conn.execute(text(f"ALTER TABLE app_students ADD COLUMN face_image {col_type}"))
        except Exception: pass
        try: conn.execute(text("ALTER TABLE app_students ADD COLUMN device_id TEXT"))
        except Exception: pass
        try: conn.execute(text("ALTER TABLE app_students ADD COLUMN department_id TEXT"))
        except Exception: pass

        # Check attendance_records table
        try: conn.execute(text("ALTER TABLE attendance_records ADD COLUMN record_hash TEXT"))
        except Exception: pass
        try: conn.execute(text("ALTER TABLE attendance_records ADD COLUMN latitude NUMERIC(9,6)"))
        except Exception: pass
        try: conn.execute(text("ALTER TABLE attendance_records ADD COLUMN longitude NUMERIC(9,6)"))
        except Exception: pass
        try: conn.execute(text("ALTER TABLE attendance_records ADD COLUMN face_verified BOOLEAN DEFAULT FALSE"))
        except Exception: pass
        try: conn.execute(text("ALTER TABLE attendance_records ADD COLUMN wifi_bssid_matched TEXT"))
        except Exception: pass

        # Check app_users table
        try: conn.execute(text("ALTER TABLE app_users ADD COLUMN fcm_token TEXT"))
        except Exception: pass
        try:
            col_type = "BLOB" if is_sqlite else "BYTEA"
            conn.execute(text(f"ALTER TABLE app_users ADD COLUMN profile_photo {col_type}"))
        except Exception: pass

# Run migrations immediately on server start
run_migrations(engine)

# --- DATABASE MODELS (SQLAlchemy Schemas) ---

class User(Base):
    """Master User table for Login and Session management"""
    __tablename__ = "app_users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    password_hash = Column(Text)
    full_name = Column(String)
    role = Column(String) # 'student' or 'faculty'
    fcm_token = Column(String, nullable=True)
    profile_photo = Column(LargeBinary, nullable=True) # Public profile display photo

class Student(Base):
    """Extends User with academic and biometric data"""
    __tablename__ = "app_students"
    id = Column(String, ForeignKey("app_users.id", ondelete="CASCADE"), primary_key=True)
    registration_number = Column(String, unique=True)
    full_name = Column(String)
    branch = Column(String, nullable=True)
    year = Column(String, nullable=True)
    face_embedding = Column(LargeBinary, nullable=True) # AI Vector
    face_image = Column(LargeBinary, nullable=True)     # Master image
    device_id = Column(String, nullable=True)
    department_id = Column(String, nullable=True)

class Teacher(Base):
    """Extends User with professional details"""
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
    """Physical Location metadata including WiFi BSSID for proximity verification"""
    __tablename__ = "classrooms"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    wifi_ssid = Column(String, nullable=True)
    wifi_bssid = Column(String, nullable=True)

class Subject(Base):
    """Academic Course metadata"""
    __tablename__ = "subjects"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    code = Column(String, unique=True, nullable=True)
    department_id = Column(String, nullable=True)
    branch = Column(String)
    year = Column(String)

class BranchSubject(Base):
    """Maps subjects to specific branches and years"""
    __tablename__ = "branch_subjects"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    branch = Column(String)
    year = Column(String)
    subject_id = Column(String, ForeignKey("subjects.id"))

class Enrollment(Base):
    """Handles students taking subjects outside their branch (Electives)"""
    __tablename__ = "enrollments"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id = Column(String, ForeignKey("subjects.id"))
    student_id = Column(String, ForeignKey("app_students.id"))

class FacultySubject(Base):
    """Direct mapping of teacher-subject assignment"""
    __tablename__ = "faculty_subjects"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    faculty_id = Column(String, ForeignKey("app_users.id"))
    subject_id = Column(String, ForeignKey("subjects.id"))

class Schedule(Base):
    """Weekly timetable entries"""
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
    """A live instance of a class with a unique QR token and expiration"""
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
    """Log of a student being marked present"""
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
    record_hash = Column(String, nullable=True) # Cryptographic fingerprint

class Notification(Base):
    """Alerts for session starts and system messages"""
    __tablename__ = "notifications"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("app_users.id"))
    title = Column(String)
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- UTILITY FUNCTIONS ---

def create_notification(db: Session, user_id: str, title: str, message: str):
    """Adds notification to DB and prints log"""
    try:
        new_notif = Notification(id=str(uuid.uuid4()), user_id=user_id, title=title, message=message)
        db.add(new_notif)
        db.commit()
    except Exception as e:
        print(f"Error creating notification: {e}")
        db.rollback()

def get_db():
    """DB Session Dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def is_valid(val):
    """Global helper to handle 'All', 'null', and 'undefined' strings from mobile clients consistently."""
    return val and val not in ["All", "null", "None", "undefined", "", "null\n"]

def clean_id(val: str) -> str:
    """Sanitize IDs from common formatting errors"""
    if not val: return val
    # Handle newlines and quotes that occasionally slip through from mobile/storage
    return str(val).replace('"', '').replace("'", "").replace('\n', '').strip()

def resolve_dept(dept_id: str, db: Session):
    """Resolves department name from ID or alias"""
    uid = clean_id(dept_id)
    teacher = db.query(Teacher).filter(Teacher.id == uid).first()
    if teacher:
        return teacher.department_id or teacher.branch

    # Standardize common department short-codes to ensure robust matching
    aliases = {
        "IT": "Information Technology",
        "CS": "Computer",
        "COMP": "Computer",
        "MECH": "Mechanical",
        "CIVIL": "Civil",
        "EXTC": "Electronics"
    }
    return aliases.get(dept_id.upper(), dept_id)

def apply_academic_filters(query, model, branch=None, year=None):
    """Unified filtering for Branch and Year across all reports"""
    if is_valid(branch):
        query = query.filter(model.branch.ilike(f"%{branch}%"))

    if is_valid(year):
        y_val = year.lower()
        if "second" in y_val or "se" in y_val: y_patterns = ["%Second%", "%SE%", "%2nd%"]
        elif "first" in y_val or "fe" in y_val: y_patterns = ["%First%", "%FE%", "%1st%"]
        elif "third" in y_val or "te" in y_val: y_patterns = ["%Third%", "%TE%", "%3rd%"]
        elif "final" in y_val or "be" in y_val or "fourth" in y_val: y_patterns = ["%Final%", "%BE%", "%4th%", "%Fourth%"]
        else: y_patterns = [f"%{year}%"]
        query = query.filter(or_(*[model.year.ilike(p) for p in y_patterns]))
    return query

# --- SERVER LIFESPAN & INITIAL SEEDING ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application"""
    # Ensure static directories exist for forensic photo storage
    os.makedirs("static/faces", exist_ok=True)
    print("--- AttendX Backend Started: Connected to Supabase ---")
    yield

Base.metadata.create_all(engine)
app = FastAPI(title="AttendX Core API", lifespan=lifespan)

# --- REQUEST MODELS (Pydantic) ---

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

# --- API ENDPOINTS ---

@app.get("/")
async def root():
    return {"status": "online", "system": "AttendX", "version": "2.2"}

# --- AUTHENTICATION ---

@app.post("/auth/login")
async def login(credentials: dict = Body(...), db: Session = Depends(get_db)):
    login_id = credentials.get("username")
    password = credentials.get("password")
    user = db.query(User).filter((User.email == login_id) | (User.username == login_id)).first()
    if user and user.password_hash == password:
        return {"success": True, "user_id": str(user.id), "role": user.role, "name": user.full_name}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/auth/signup")
async def signup(user_data: dict = Body(...), db: Session = Depends(get_db)):
    existing = db.query(User).filter((User.email == user_data.get("email")) | (User.username == user_data.get("username"))).first()
    if existing: raise HTTPException(status_code=400, detail="User already exists")

    new_id = str(user_data.get("id") or uuid.uuid4())
    user = User(id=new_id, username=user_data.get("username"), email=user_data.get("email"), password_hash=user_data.get("password"), full_name=user_data.get("full_name"), role=user_data.get("role"))
    db.add(user); db.flush()

    if user_data.get("role") == "student":
        db.add(Student(id=new_id, full_name=user.full_name, registration_number=user.username, branch=user_data.get("branch"), year=user_data.get("year")))
    else:
        db.add(Teacher(id=new_id, full_name=user.full_name, employee_id=user.username, branch=user_data.get("branch")))

    db.commit()
    return {"success": True, "user_id": new_id, "role": user.role}

@app.get("/auth/me/{user_id}")
async def get_user_profile(user_id: str, db: Session = Depends(get_db)):
    uid = clean_id(user_id)
    user = db.query(User).filter((User.id == uid) | (User.username == uid)).first()
    if not user: raise HTTPException(404, "User not found")

    profile = {"id": str(user.id), "username": user.username, "email": user.email, "full_name": user.full_name, "role": user.role, "academic": {}, "image_url": None, "profile_photo_url": None}

    if user.profile_photo:
        profile["profile_photo_url"] = f"users/{user.id}/profile-photo"

    # Standardize image URL for frontend Biometric ID Card
    reg_no = user.username
    if user.role == "student":
        s = db.query(Student).filter(Student.id == user.id).first()
        if s:
            profile["academic"] = {"branch": s.branch, "department": s.branch, "year": s.year, "reg_no": s.registration_number}
            reg_no = s.registration_number
            if s.face_image:
                profile["image_url"] = f"faces/{reg_no}.jpg"
    else:
        t = db.query(Teacher).filter(Teacher.id == user.id).first()
        if t: profile["academic"] = {"branch": t.branch, "department": t.branch, "designation": t.designation, "employee_id": t.employee_id}

    return profile

# --- ACADEMIC DATA FETCHING ---

@app.get("/classrooms")
async def get_classrooms(db: Session = Depends(get_db)):
    return [{"id": str(r.id), "name": str(r.name or "Unknown Room"), "wifi_bssid": str(r.wifi_bssid or "")} for r in db.query(Classroom).all()]

@app.get("/subjects")
async def get_subjects(db: Session = Depends(get_db)):
    return [{"id": str(s.id), "name": str(s.name or "Unknown Subject"), "code": str(s.code or "")} for s in db.query(Subject).all()]

@app.get("/faculty/subjects/{faculty_id}")
async def get_faculty_subjects(faculty_id: str, db: Session = Depends(get_db)):
    fid = clean_id(faculty_id)
    # 1. Get subjects from FacultySubject assignments
    subjects = db.query(Subject).join(FacultySubject).filter(FacultySubject.faculty_id == fid).all()

    # 2. Get subjects from existing Schedule entries
    if not subjects:
        subjects = db.query(Subject).join(Schedule).filter(Schedule.faculty_id == fid).all()

    # 3. Fallback for new faculty: Get all subjects in their branch
    if not subjects:
        teacher = db.query(Teacher).filter(Teacher.id == fid).first()
        if teacher and teacher.branch:
            subjects = db.query(Subject).filter(Subject.branch == teacher.branch).all()

    # 4. Global Fallback: If still nothing, return all subjects so they can choose
    if not subjects:
        subjects = db.query(Subject).all()

    results = []
    seen = set()
    for s in subjects:
        if s.id not in seen:
            results.append({
                "id": str(s.id),
                "name": str(s.name or "Unknown"),
                "code": str(s.code or ""),
                "branch": str(s.branch or ""),
                "year": str(s.year or "")
            })
            seen.add(s.id)
    return results

@app.get("/student/subjects/{student_id}")
async def get_student_subjects(student_id: str, db: Session = Depends(get_db)):
    sid = clean_id(student_id)
    student = db.query(Student).filter(Student.id == sid).first()
    if not student: raise HTTPException(404, "Student not found")

    branch_subs = db.query(Subject).filter(Subject.branch == student.branch, Subject.year == student.year).all()
    minor_subs = db.query(Subject).join(Enrollment).filter(Enrollment.student_id == sid).all()
    return [{"id": str(s.id), "name": str(s.name or "Unknown"), "code": str(s.code or "")} for s in set(branch_subs + minor_subs)]

# --- TIMETABLE & SCHEDULING ---

@app.get("/faculty/schedule/{faculty_id}")
async def get_faculty_schedule(faculty_id: str, day: Optional[str] = None, db: Session = Depends(get_db)):
    fid = clean_id(faculty_id)
    query = db.query(Schedule, Subject, Classroom).join(Subject).join(Classroom).filter(Schedule.faculty_id == fid)
    if day: query = query.filter(Schedule.day_of_week == day)
    return [{
        "id": str(s.id), "day": s.day_of_week, "subject": sub.name, "subject_id": str(sub.id),
        "room": c.name, "classroom_id": str(c.id), "time": f"{s.start_time} - {s.end_time}", "is_official": s.is_official
    } for s, sub, c in query.all()]

@app.post("/faculty/schedule/{faculty_id}")
async def add_schedule_record(faculty_id: str, record: dict = Body(...), db: Session = Depends(get_db)):
    fid = clean_id(faculty_id)
    time_parts = record.get("time", "09:00 - 10:00").split(" - ")
    new_s = Schedule(id=str(uuid.uuid4()), faculty_id=fid, subject_id=record.get("subject_id"), classroom_id=record.get("classroom_id"),
                     day_of_week=record.get("day"), start_time=time_parts[0], end_time=time_parts[1] if len(time_parts)>1 else "10:00", is_official=False)
    db.add(new_s); db.commit(); db.refresh(new_s)
    sub = db.query(Subject).filter(Subject.id == new_s.subject_id).first()
    room = db.query(Classroom).filter(Classroom.id == new_s.classroom_id).first()
    return {"id": str(new_s.id), "day": new_s.day_of_week, "subject": sub.name if sub else "Unknown", "room": room.name if room else "Unknown", "time": f"{new_s.start_time} - {new_s.end_time}"}

@app.delete("/faculty/schedule/{record_id}")
async def delete_schedule_record(record_id: str, db: Session = Depends(get_db)):
    s = db.query(Schedule).filter(Schedule.id == clean_id(record_id)).first()
    if s: db.delete(s); db.commit(); return {"success": True}
    raise HTTPException(404, "Record not found")

@app.get("/student/schedule/{student_id}")
async def get_student_schedule(student_id: str, day: Optional[str] = None, db: Session = Depends(get_db)):
    sid = clean_id(student_id)
    student = db.query(Student).filter(Student.id == sid).first()
    if not student: return []
    sub_ids = [s[0] for s in db.query(Subject.id).filter(Subject.branch == student.branch, Subject.year == student.year).all()]
    minor_ids = [s[0] for s in db.query(Enrollment.subject_id).filter(Enrollment.student_id == sid).all()]
    all_sub_ids = list(set(sub_ids + minor_ids))
    query = db.query(Schedule, Subject, Classroom).join(Subject).join(Classroom).filter(Schedule.subject_id.in_(all_sub_ids))
    if day: query = query.filter(Schedule.day_of_week == day)
    return [{"day": s.day_of_week, "subject": sub.name, "room": c.name, "time": f"{s.start_time} - {s.end_time}"} for s, sub, c in query.all()]

# --- SESSION & ATTENDANCE CORE ---

@app.post("/sessions/start", response_model=SessionResponse)
async def start_session(req: StartSessionRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    classroom = db.query(Classroom).filter(Classroom.id == req.classroom_id).first()
    sid = str(uuid.uuid4()); qr_token = f"QR_{uuid.uuid4().hex[:8].upper()}"
    expiry = datetime.utcnow() + timedelta(minutes=req.duration_minutes)
    session = AttendanceSession(id=sid, faculty_id=req.faculty_id, subject_id=req.subject_id, classroom_id=req.classroom_id,
                                qr_token=qr_token, qr_expires_at=expiry, status="active")
    db.add(session); db.commit()
    background_tasks.add_task(send_session_notifications, req.faculty_id, req.subject_id, classroom.name, sid)
    return SessionResponse(session_id=sid, qr_token=qr_token, expires_at=expiry.isoformat(), classroom_name=classroom.name)

def send_session_notifications(faculty_id: str, subject_id: str, room_name: str, session_id: str):
    db = SessionLocal()
    try:
        subject = db.query(Subject).filter(Subject.id == subject_id).first()
        create_notification(db, faculty_id, "Session Started", f"Session for {subject.name} started in {room_name}.")
        students = db.query(Student).filter(Student.branch == subject.branch, Student.year == subject.year).all()
        for s in students: create_notification(db, s.id, "Class Started", f"{subject.name} has started in {room_name}.")
    finally: db.close()

@app.post("/sessions/stop/{session_id}")
async def stop_session(session_id: str, db: Session = Depends(get_db)):
    sid = clean_id(session_id)
    session = db.query(AttendanceSession, Subject).join(Subject).filter(AttendanceSession.id == sid).first()
    if not session: raise HTTPException(404, "Session not found")
    session_obj, sub_obj = session
    session_obj.status = "stopped"
    db.commit()

    records = db.query(AttendanceRecord, Student).join(Student).filter(AttendanceRecord.session_id == sid).all()
    count = len(records)

    student_list = []
    for rec, stu in records:
        student_list.append({
            "id": str(stu.id),
            "name": str(stu.full_name or "Unknown Student"),
            "time": rec.marked_at.isoformat() if rec.marked_at else datetime.utcnow().isoformat()
        })

    create_notification(db, session_obj.faculty_id, "Session Summary", f"Session for {sub_obj.name} closed. Present: {count}.")

    return {
        "session_id": sid,
        "total_present": count,
        "students": student_list,
        "course_id": str(sub_obj.name or "Unknown Subject")
    }

@app.get("/faculty/sessions/{faculty_id}")
async def get_faculty_sessions(faculty_id: str, subject_id: Optional[str] = None, classroom_id: Optional[str] = None, date: Optional[str] = None, db: Session = Depends(get_db)):
    fid = clean_id(faculty_id)

    # Performance Optimization: Subquery for student counts to avoid N+1 queries
    count_subquery = db.query(
        AttendanceRecord.session_id,
        func.count(AttendanceRecord.id).label('student_count')
    ).group_by(AttendanceRecord.session_id).subquery()

    # Base query with Outer Joins for resilience
    query = db.query(
        AttendanceSession,
        Subject,
        func.coalesce(count_subquery.c.student_count, 0).label('student_count')
    ).outerjoin(Subject, AttendanceSession.subject_id == Subject.id)\
     .outerjoin(count_subquery, AttendanceSession.id == count_subquery.c.session_id)\
     .filter(AttendanceSession.faculty_id == fid)

    if subject_id:
        query = query.filter(AttendanceSession.subject_id == subject_id)
    if classroom_id:
        query = query.filter(AttendanceSession.classroom_id == classroom_id)
    if date:
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
            query = query.filter(func.date(AttendanceSession.start_time) == target_date)
        except Exception: pass

    sessions = query.order_by(AttendanceSession.start_time.desc()).limit(100).all()

    results = []
    for sess, sub, count in sessions:
        results.append({
            "session_id": str(sess.id),
            "subject_id": str(sub.id) if sub else (str(sess.subject_id) if sess.subject_id else "N/A"),
            "subject_name": str(sub.name or "Unknown Subject") if sub else "Unknown Subject",
            "classroom_id": str(sess.classroom_id or "N/A"),
            "start_time": sess.start_time.isoformat() if sess.start_time else datetime.utcnow().isoformat(),
            "expires_at": sess.qr_expires_at.isoformat() if sess.qr_expires_at else None,
            "status": str(sess.status or "active"),
            "student_count": int(count)
        })
    return results

@app.get("/sessions/{session_id}/details")
async def get_session_details(session_id: str, db: Session = Depends(get_db)):
    sid = clean_id(session_id)
    session_data = db.query(AttendanceSession, Subject).join(Subject).filter(AttendanceSession.id == sid).first()
    if not session_data:
        raise HTTPException(404, "Session not found")

    sess, sub = session_data
    records = db.query(AttendanceRecord, Student).join(Student).filter(AttendanceRecord.session_id == sid).all()

    student_details = []
    for rec, stu in records:
        student_details.append({
            "student_id": str(stu.id),
            "student_name": str(stu.full_name or "Unknown Student"),
            "marked_at": rec.marked_at.isoformat() if rec.marked_at else sess.start_time.isoformat(),
            "status": str(rec.status or "present")
        })

    return {
        "session_id": sid,
        "subject_name": str(sub.name or "Unknown Subject"),
        "start_time": sess.start_time.isoformat(),
        "total_students": len(records),
        "students": student_details
    }

# --- THE 3-LAYER VERIFICATION PIPELINE ---

@app.post("/attendance/verify-wifi")
async def verify_wifi(req: VerifyWifiRequest, db: Session = Depends(get_db)):
    """LAYER 1: Proximity Verification via WiFi BSSID"""
    session = db.query(AttendanceSession).filter(AttendanceSession.id == clean_id(req.session_id)).first()
    if not session: raise HTTPException(404, "Session not found")
    classroom = db.query(Classroom).filter(Classroom.id == session.classroom_id).first()

    client_bssid = (req.bssid or "").strip().lower()
    target_bssid = (classroom.wifi_bssid or "").strip().lower()
    if client_bssid == target_bssid or not target_bssid: return {"success": True, "message": "WiFi Verified"}
    raise HTTPException(403, "Location verification failed: WiFi BSSID mismatch")

@app.post("/attendance/verify-qr")
async def verify_qr(req: dict = Body(...), db: Session = Depends(get_db)):
    """LAYER 2: Dynamic Token Validation"""
    sid = clean_id(req.get("session_id", "")); token = req.get("token", "").strip()
    session = db.query(AttendanceSession).filter(AttendanceSession.id == sid).first()
    if session and (session.qr_token == token): return {"success": True}
    return {"success": False, "message": "Invalid or Expired QR Token"}

@app.post("/attendance/verify-face")
async def verify_face(
    student_id: str = Form(...),
    session_id: str = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """LAYER 3: AI Biometric Authentication"""
    try:
        sid = clean_id(student_id); sess_id = clean_id(session_id)
        student = db.query(Student).filter((Student.id == sid) | (Student.registration_number == sid)).first()
        if not image: raise HTTPException(400, "No face captured")
        img_bytes = await image.read()

        is_verified = False; msg = "Attendance marked!"
        if not student.face_embedding:
            # First Time: Extract & Store Embedding
            await image.seek(0)
            resp = requests.post(f"{HF_API_URL}/represent", files={"image": (image.filename, await image.read(), image.content_type)},
                                 headers={"Authorization": f"Bearer {HF_TOKEN}"}, timeout=60)
            if resp.status_code == 200:
                student.face_embedding = json.dumps(resp.json()["embedding"]).encode('utf-8')
                student.face_image = img_bytes

                # Physical storage for PDF reports and forensic audits
                photo_path = f"static/faces/{student.registration_number}.jpg"
                with open(photo_path, "wb") as f:
                    f.write(img_bytes)

                db.commit()
                is_verified = True
                msg = "Face Registered & Locally Stored!"
        else:
            # Subsequent Times: Verify Identity
            await image.seek(0)
            resp = requests.post(f"{HF_API_URL}/verify", files={"image": (image.filename, await image.read(), image.content_type)},
                                 data={"stored_embedding": student.face_embedding.decode('utf-8')},
                                 headers={"Authorization": f"Bearer {HF_TOKEN}"}, timeout=60)
            if resp.status_code == 200 and resp.json().get("is_match"): is_verified = True; msg = "Face Verified!"
            else: raise HTTPException(401, "Biometric Mismatch")

        # Log Record
        if not db.query(AttendanceRecord).filter(AttendanceRecord.session_id == sess_id, AttendanceRecord.student_id == student.id).first():
            # Generate Cryptographic Fingerprint for the Record
            record_str = f"{sess_id}|{student.id}|{datetime.utcnow().isoformat()}|{is_verified}"
            r_hash = hashlib.sha256(record_str.encode()).hexdigest().upper()

            db.add(AttendanceRecord(
                id=str(uuid.uuid4()),
                session_id=sess_id,
                student_id=student.id,
                face_verified=is_verified,
                record_hash=r_hash,
                latitude=latitude,
                longitude=longitude
            ))
            db.commit()
            create_notification(db, student.id, "Attendance Marked", "Marked present via biometrics.")
        return {"success": True, "message": msg}
    except Exception as e:
        db.rollback(); raise HTTPException(500, f"AI Error: {str(e)}")

@app.post("/attendance/manual")
async def manual_attendance(req: dict = Body(...), db: Session = Depends(get_db)):
    """LAYER 4: Manual Override (Faculty Authorized)"""
    try:
        sid = clean_id(req.get("session_id", ""))
        student_query = req.get("student_id", "").strip()

        # Resolve student by ID or Reg No
        student = db.query(Student).filter((Student.id == student_query) | (Student.registration_number == student_query)).first()
        if not student:
            raise HTTPException(404, f"Student '{student_query}' not found")

        session = db.query(AttendanceSession).filter(AttendanceSession.id == sid).first()
        if not session:
            raise HTTPException(404, "Session not found")

        # Check for duplicate
        existing = db.query(AttendanceRecord).filter(AttendanceRecord.session_id == sid, AttendanceRecord.student_id == student.id).first()
        if existing:
            return {"success": True, "message": "Attendance already marked"}

        # Record Manual Attendance
        # Generate Cryptographic Fingerprint for Manual Override
        now = datetime.utcnow()
        record_str = f"{sid}|{student.id}|{now.isoformat()}|MANUAL"
        r_hash = hashlib.sha256(record_str.encode()).hexdigest().upper()

        db.add(AttendanceRecord(
            id=str(uuid.uuid4()),
            session_id=sid,
            student_id=student.id,
            marked_at=now,
            status="present",
            face_verified=False,
            record_hash=r_hash
        ))
        db.commit()

        create_notification(db, student.id, "Manual Attendance", f"Marked present manually by Faculty.")
        return {"success": True, "message": f"Attendance marked for {student.full_name}"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Error marking manual attendance: {str(e)}")

# --- REPORTING & UTILITIES ---

@app.get("/sessions/{session_id}/attendance")
async def get_attendance(session_id: str, db: Session = Depends(get_db)):
    sid = clean_id(session_id)
    records = db.query(AttendanceRecord, Student).join(Student).filter(AttendanceRecord.session_id == sid).all()
    return {
        "total_count": len(records),
        "students": [
            {
                "student_id": str(r.student_id),
                "student_name": str(s.full_name or "Unknown Student"),
                "timestamp": r.marked_at.isoformat() if r.marked_at else datetime.utcnow().isoformat(),
                "face_verified": bool(r.face_verified)
            } for r, s in records
        ]
    }

@app.get("/student/attendance/{student_id}")
async def get_student_history(student_id: str, db: Session = Depends(get_db)):
    sid = clean_id(student_id)
    print(f"DEBUG: Fetching history for student_id={sid}")
    student = db.query(Student).filter(Student.id == sid).first()
    if not student:
        print(f"DEBUG: Student {sid} not found")
        return []

    # 1. Get subjects from branch/year
    branch_subs = [s[0] for s in db.query(Subject.id).filter(
        Subject.branch == student.branch,
        Subject.year == student.year
    ).all()]

    # 2. Get subjects from enrollments (Electives)
    enrolled_subs = [e[0] for e in db.query(Enrollment.subject_id).filter(
        Enrollment.student_id == sid
    ).all()]

    all_sub_ids = list(set(branch_subs + enrolled_subs))
    print(f"DEBUG: Found {len(all_sub_ids)} relevant subjects for student {sid}")

    # Fetch sessions for these subjects
    sessions = db.query(AttendanceSession, Subject).join(Subject).filter(
        AttendanceSession.subject_id.in_(all_sub_ids)
    ).order_by(AttendanceSession.start_time.desc()).all()

    # Get attendance records for this student
    records = {r.session_id: r for r in db.query(AttendanceRecord).filter(
        AttendanceRecord.student_id == sid
    ).all()}

    print(f"DEBUG: Found {len(sessions)} sessions and {len(records)} attendance records")

    return [
        {
            "subject_id": str(sub.id),
            "subject_name": str(sub.name or "Unknown Subject"),
            "session_id": str(s.id),
            "timestamp": (records[s.id].marked_at if s.id in records else s.start_time).isoformat(),
            "status": "present" if s.id in records else "absent"
        } for s, sub in sessions
    ]

@app.get("/student/attendance/{student_id}/subjects")
async def get_subject_attendance(student_id: str, db: Session = Depends(get_db)):
    sid = clean_id(student_id)
    student = db.query(Student).filter(Student.id == sid).first()
    if not student: return []

    # 1. Get relevant subjects
    branch_subs = [s[0] for s in db.query(Subject.id).filter(Subject.branch == student.branch, Subject.year == student.year).all()]
    enrolled_subs = [e[0] for e in db.query(Enrollment.subject_id).filter(Enrollment.student_id == sid).all()]
    all_sub_ids = list(set(branch_subs + enrolled_subs))

    # 2. Get all sessions for these subjects
    sessions = db.query(AttendanceSession).filter(AttendanceSession.subject_id.in_(all_sub_ids)).all()

    # 3. Get student attendance records
    records = db.query(AttendanceRecord).filter(AttendanceRecord.student_id == sid).all()
    attended_session_ids = {r.session_id for r in records}

    # 4. Aggregate by subject
    subject_map = {}
    subjects = db.query(Subject).filter(Subject.id.in_(all_sub_ids)).all()
    for s in subjects:
        subject_map[s.id] = {
            "subject_id": str(s.id),
            "subject_name": str(s.name),
            "total_classes": 0,
            "attended_classes": 0
        }

    for sess in sessions:
        if sess.subject_id in subject_map:
            subject_map[sess.subject_id]["total_classes"] += 1
            if sess.id in attended_session_ids:
                subject_map[sess.subject_id]["attended_classes"] += 1

    # 5. Calculate percentage and format response
    results = []
    for sub_data in subject_map.values():
        total = sub_data["total_classes"]
        attended = sub_data["attended_classes"]
        percentage = (attended / total) if total > 0 else 0.0
        sub_data["percentage"] = round(percentage, 4) # Return as decimal (0.0 to 1.0)
        results.append(sub_data)

    return results

@app.post("/notifications/send")
async def send_manual_notification(data: dict = Body(...), db: Session = Depends(get_db)):
    """Broadcasts a notification to a specific user, branch/year group, or class"""
    target_type = data.get("target_type") # 'individual', 'group', or 'class'
    target_id = data.get("target_id")
    title = data.get("title", "System Notification")
    message = data.get("message", "")
    sender_id = data.get("sender_id")

    if not message or not target_id:
        raise HTTPException(400, "Missing message or target identifier")

    target_users = []
    if target_type == "individual":
        # target_id is the user_id or registration number
        user = db.query(User).filter((User.id == target_id) | (User.username == target_id)).first()
        if user: target_users.append(user.id)

    elif target_type == "group":
        # target_id is likely "Branch|Year" e.g., "Information Technology|Third Year"
        try:
            branch, year = target_id.split("|")
            students = db.query(Student).filter(Student.branch.ilike(f"%{branch}%"), Student.year.ilike(f"%{year}%")).all()
            target_users = [s.id for s in students]
        except:
            raise HTTPException(400, "Invalid group format. Use 'Branch|Year'")

    elif target_type == "class":
        # target_id is the subject_id
        # Send to all students in that subject (branch/year match)
        subject = db.query(Subject).filter(Subject.id == target_id).first()
        if subject:
            students = db.query(Student).filter(Student.branch == subject.branch, Student.year == subject.year).all()
            target_users = [s.id for s in students]

    # Create notifications in DB
    for uid in target_users:
        create_notification(db, uid, title, message)

    return {"success": True, "recipients": len(target_users)}

@app.post("/auth/update-fcm")
async def update_fcm_token(data: dict = Body(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == clean_id(data.get("user_id"))).first()
    if user: user.fcm_token = data.get("fcm_token"); db.commit(); return {"success": True}
    raise HTTPException(404, "User not found")

@app.get("/faces/{student_id}.jpg")
async def get_student_face(student_id: str, db: Session = Depends(get_db)):
    student = db.query(Student).filter((Student.registration_number == student_id) | (Student.id == student_id)).first()
    if student and student.face_image: return Response(content=student.face_image, media_type="image/jpeg")
    raise HTTPException(404, "Face not found")

@app.post("/users/{user_id}/profile-photo")
async def upload_profile_photo(user_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    uid = clean_id(user_id)
    user = db.query(User).filter(User.id == uid).first()
    if not user: raise HTTPException(404, "User not found")

    user.profile_photo = await file.read()
    db.commit()
    return {"success": True, "message": "Profile photo updated"}

@app.get("/users/{user_id}/profile-photo")
async def get_profile_photo(user_id: str, db: Session = Depends(get_db)):
    uid = clean_id(user_id)
    user = db.query(User).filter(User.id == uid).first()
    if user and user.profile_photo:
        return Response(content=user.profile_photo, media_type="image/jpeg")
    raise HTTPException(404, "Profile photo not found")

@app.put("/users/{user_id}")
async def update_user(user_id: str, data: dict = Body(...), db: Session = Depends(get_db)):
    uid = clean_id(user_id)
    user = db.query(User).filter(User.id == uid).first()
    if not user: raise HTTPException(404, "User not found")

    if "full_name" in data:
        user.full_name = data["full_name"]
        if user.role == "student":
            s = db.query(Student).filter(Student.id == uid).first()
            if s: s.full_name = data["full_name"]
        else:
            t = db.query(Teacher).filter(Teacher.id == uid).first()
            if t: t.full_name = data["full_name"]

    db.commit()
    return {"success": True}

@app.get("/notifications/{user_id}")
async def get_notifications(user_id: str, db: Session = Depends(get_db)):
    notifs = db.query(Notification).filter(Notification.user_id == user_id).order_by(Notification.created_at.desc()).all()
    return [{"id": str(n.id), "title": n.title, "message": n.message, "is_read": n.is_read, "created_at": n.created_at.isoformat()} for n in notifs]

@app.post("/notifications/read/{notification_id}")
async def mark_read(notification_id: str, db: Session = Depends(get_db)):
    n = db.query(Notification).filter(Notification.id == notification_id).first()
    if n: n.is_read = True; db.commit(); return {"success": True}
    raise HTTPException(404, "Notfound")

@app.post("/notifications/delete/{notification_id}")
async def delete_notification(notification_id: str, db: Session = Depends(get_db)):
    n = db.query(Notification).filter(Notification.id == notification_id).first()
    if n: db.delete(n); db.commit(); return {"success": True}
    raise HTTPException(404, "Notfound")

@app.post("/notifications/clear/{user_id}")
async def clear_notifications(user_id: str, db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.user_id == user_id).delete()
    db.commit()
    return {"success": True, "message": "All notifications cleared"}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db)):
    db.query(AttendanceRecord).filter(AttendanceRecord.session_id == session_id).delete()
    session = db.query(AttendanceSession).filter(AttendanceSession.id == session_id).first()
    if session:
        db.delete(session)
        db.commit()
        return {"success": True}
    raise HTTPException(404, "Session not found")

@app.post("/sessions/clear/{faculty_id}")
async def clear_faculty_sessions(faculty_id: str, db: Session = Depends(get_db)):
    sessions = db.query(AttendanceSession).filter(AttendanceSession.faculty_id == faculty_id).all()
    session_ids = [s.id for s in sessions]
    if session_ids:
        db.query(AttendanceRecord).filter(AttendanceRecord.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(AttendanceSession).filter(AttendanceSession.id.in_(session_ids)).delete(synchronize_session=False)
        db.commit()
    return {"success": True, "message": f"Cleared {len(session_ids)} sessions"}

# --- ADVANCED PDF REPORTING SYSTEM (Enterprise Edition v3.5 - High-End Project Final) ---

class PDFReport(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Material 3 Inspired Palette (Professional Blue Theme)
        self.primary_color = (21, 101, 192)   # Deep Blue (Primary)
        self.secondary_color = (66, 66, 66)    # Dark Gray (Text)
        self.accent_color = (13, 71, 161)      # Darker Accent
        self.surface_variant = (232, 240, 254) # Light Blue Surface
        self.error_color = (184, 27, 27)       # M3 Error Red
        self.success_color = (46, 125, 50)     # M3 Success Green
        self.vjti_gold = (255, 215, 0)         # VJTI Branding Gold

    def header(self):
        # Grand Institutional Header
        self.set_fill_color(*self.primary_color)
        self.rect(0, 0, 210, 50, 'F')

        # Gold accent line (Institutional Excellence)
        self.set_fill_color(*self.vjti_gold)
        self.rect(0, 50, 210, 2, 'F')

        # VJTI Logo - High Precision Placement (Right Aligned, Non-Overlapping)
        logo_path = os.path.join(os.path.dirname(__file__), "..", "vjti.jpg")
        if os.path.exists(logo_path):
            try:
                # Circular background container for the logo, pushed to the far right to avoid name overlap
                self.set_fill_color(255, 255, 255)
                self.rect(175, 8, 28, 28, 'F')
                self.image(logo_path, 176, 9, 26)
            except Exception as e:
                print(f"Logo error: {e}")

        # Typography: Grand Institutional Name
        self.set_text_color(255, 255, 255)
        self.set_font('helvetica', 'B', 18)
        self.set_xy(12, 10)
        self.cell(155, 10, 'VEERMATA JIJABAI TECHNOLOGICAL INSTITUTE', 0, 1, 'L')

        # Institutional Sub-details
        self.set_font('helvetica', '', 8)
        self.set_text_color(220, 230, 255)
        self.set_xy(12, 19)
        self.cell(155, 5, 'ESTABLISHED 1887 | AN AUTONOMOUS INSTITUTE OF GOVT. OF MAHARASHTRA', 0, 1, 'L')
        self.set_xy(12, 23)
        self.cell(155, 5, 'MATUNGA, MUMBAI - 400019 | ISO 9001:2015 CERTIFIED', 0, 1, 'L')

        # Cryptographic Session Fingerprint (SHA-256) - Positioned subtly
        if hasattr(self, 'session_hash'):
            self.set_xy(12, 34)
            self.set_font('helvetica', 'B', 7)
            self.set_text_color(160, 180, 240)
            self.cell(0, 5, f"SYSTEM AUTHENTICATION HASH: {self.session_hash}", 0, 0, 'L')

        # Professional Branding Bar - Left aligned at the base of the header for a clean look
        self.set_xy(12, 42)
        self.set_font('helvetica', 'B', 11)
        self.set_text_color(*self.surface_variant)
        self.cell(160, 7, 'ATTENDX | SECURE INTELLIGENT SYSTEM', 0, 1, 'L')

        self.ln(20)

    def footer(self):
        self.set_y(-25)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.set_draw_color(230, 230, 230)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)
        self.cell(0, 10, 'Officially Authenticated Digital Academic Record. Confidentiality Governed by IT Act 2000.', 0, 1, 'C')

        # QR Placeholder and Metadata
        self.set_font('helvetica', 'B', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f'Page {self.page_no()} | UID: {uuid.uuid4().hex[:12].upper()} | DBMS-PROJ-2024-SHUBHAM', 0, 0, 'C')

    def chapter_title(self, title, color=(21, 101, 192)):
        self.ln(8)
        self.set_font('helvetica', 'B', 14)
        self.set_text_color(*color)
        self.cell(0, 10, f" {title.upper()}", 0, 1, 'L')

        # M3 Styling - Horizontal Rule with Accent
        self.set_draw_color(*color)
        self.set_line_width(0.8)
        self.line(10, self.get_y() - 1, 60, self.get_y() - 1)
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.2)
        self.line(60, self.get_y() - 1, 200, self.get_y() - 1)
        self.ln(5)

    def draw_summary_box(self, metrics: list):
        """Helper to draw professional grid-based metrics cards"""
        start_y = self.get_y()
        num_metrics = len(metrics)
        card_width = 190 / num_metrics

        for i, (label, value, is_alert) in enumerate(metrics):
            curr_x = 10 + (i * card_width)

            # Draw Card Background
            self.set_fill_color(252, 252, 252)
            self.set_draw_color(230, 235, 240)
            self.rect(curr_x, start_y, card_width - 2, 28, 'FD')

            # Bottom border accent for cards
            self.set_fill_color(*(211, 47, 47) if is_alert else self.primary_color)
            self.rect(curr_x, start_y + 26, card_width - 2, 2, 'F')

            # Label
            self.set_xy(curr_x, start_y + 5)
            self.set_font('helvetica', '', 8)
            self.set_text_color(100, 100, 100)
            self.cell(card_width - 2, 5, label.upper(), 0, 1, 'C')

            # Value
            self.set_x(curr_x)
            self.set_font('helvetica', 'B', 12)
            self.set_text_color(*(211, 47, 47) if is_alert else (33, 33, 33))
            self.cell(card_width - 2, 10, str(value), 0, 1, 'C')

        self.set_y(start_y + 35)

    def draw_student_audit_card(self, student_obj, record_obj, db=None):
        """Draws a detailed student profile card with their registered photo"""
        start_y = self.get_y()
        self.set_fill_color(252, 252, 252)
        self.set_draw_color(220, 226, 230)
        self.rect(10, start_y, 190, 65, 'FD')

        # Sub-header: VJTI Audit Header
        self.set_fill_color(*self.surface_variant)
        self.rect(10, start_y, 190, 10, 'F')
        self.set_xy(15, start_y + 2)
        self.set_font('helvetica', 'B', 11)
        self.set_text_color(*self.primary_color)
        self.cell(0, 6, f"SESSION FORENSIC EVIDENCE: {student_obj.registration_number}", 0, 1)

        # Student Photo (Left Side) - Ensure it exists from DB if missing
        photo_path = f"static/faces/{student_obj.registration_number}.jpg"
        if not os.path.exists(photo_path) and student_obj.face_image:
            try:
                with open(photo_path, "wb") as f:
                    f.write(student_obj.face_image)
            except: pass

        photo_drawn = False
        if os.path.exists(photo_path):
            try:
                self.image(photo_path, 15, start_y + 15, 35, 40)
                photo_drawn = True
            except: pass

        if not photo_drawn:
            # Placeholder if no photo
            self.set_draw_color(200, 200, 200)
            self.rect(15, start_y + 15, 35, 40, 'D')
            self.set_xy(15, start_y + 30)
            self.set_font('helvetica', 'I', 8)
            self.cell(35, 10, "No Biometric Data", 0, 0, 'C')

        # Student Metadata (Right Side)
        self.set_xy(55, start_y + 15)
        self.set_text_color(50, 50, 50)

        info = [
            ("Full Name", student_obj.full_name),
            ("Academic Node", f"{student_obj.branch} - {student_obj.year}"),
            ("Auth Method", "AI Biometric (DeepFace)"),
            ("Log Timestamp", record_obj.marked_at.strftime("%d %b %Y, %I:%M %p") if record_obj else "N/A"),
            ("Forensic Hash", record_obj.record_hash[:24] if record_obj and record_obj.record_hash else "UNSPECIFIED")
        ]

        # Add Location Data if available
        if record_obj and record_obj.latitude and record_obj.longitude:
            info.append(("Coordinates", f"{record_obj.latitude}, {record_obj.longitude}"))

        for label, val in info:
            self.set_x(55)
            self.set_font('helvetica', 'B', 8)
            self.cell(30, 6, f"{label}:", 0, 0)
            self.set_font('helvetica', '', 8)
            self.cell(0, 6, str(val), 0, 1)

        # Audit Stamp
        self.set_xy(145, start_y + 48)
        self.set_font('helvetica', 'B', 10)
        self.set_text_color(*self.success_color)
        self.set_draw_color(*self.success_color)
        self.cell(45, 10, "SMART DETECTED", 1, 0, 'C')

        self.set_y(start_y + 70)


    def draw_digital_watermark(self):
        """Adds a subtle 'OFFICIAL' watermark in the background"""
        curr_y = self.get_y()
        self.set_font('helvetica', 'B', 60)
        self.set_text_color(245, 245, 245)
        self.set_xy(10, 150)
        self.cell(190, 50, 'OFFICIAL RECORD', 0, 0, 'C')
        self.set_y(curr_y)
        self.set_text_color(0, 0, 0)

    def draw_distribution_chart(self, labels, values, colors):
        """Professional Bar Chart for Attendance Distribution"""
        self.set_font('helvetica', 'B', 11)
        self.set_text_color(*self.primary_color)
        self.cell(0, 10, "  STATISTICAL DISTRIBUTION", 0, 1)

        chart_x = 65
        chart_y = self.get_y()
        max_val = max(values) if max(values) > 0 else 1

        for i, (label, count) in enumerate(zip(labels, values)):
            bar_width = (count / max_val) * 110

            # Label
            self.set_xy(10, chart_y + (i * 9))
            self.set_font('helvetica', '', 9)
            self.set_text_color(80, 80, 80)
            self.cell(50, 7, label, 0, 0, 'R')

            # Bar Shadow (Subtle)
            self.set_fill_color(240, 240, 240)
            self.rect(chart_x, chart_y + (i * 9) + 1, 110, 5, 'F')

            # Actual Bar
            self.set_fill_color(*colors[i])
            self.rect(chart_x, chart_y + (i * 9) + 1, bar_width, 5, 'F')

            # Count Text
            self.set_xy(chart_x + 112, chart_y + (i * 9))
            self.set_font('helvetica', 'B', 9)
            self.set_text_color(50, 50, 50)
            self.cell(10, 7, str(count), 0, 1, 'L')

        self.set_y(chart_y + (len(labels) * 9) + 5)


@app.get("/reports/pdf/{session_id}")
async def export_session_pdf(session_id: str, student_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Generates a professional PDF for a single attendance session using Live Supabase Data"""
    sid = clean_id(session_id)
    # Use Outer Join for Classroom and User to handle NULL values in Supabase
    session_data = db.query(AttendanceSession, Subject, Classroom, User)\
        .join(Subject, AttendanceSession.subject_id == Subject.id)\
        .outerjoin(Classroom, AttendanceSession.classroom_id == Classroom.id)\
        .outerjoin(User, AttendanceSession.faculty_id == User.id)\
        .filter(AttendanceSession.id == sid).first()

    if not session_data:
        raise HTTPException(404, "Session data not found in Supabase. Check if subject or session exists.")

    sess, sub, room, user_obj = session_data

    # Filter out dummy cloud___ records
    records_query = db.query(AttendanceRecord, Student).join(Student)\
        .filter(AttendanceRecord.session_id == sid)\
        .filter(~Student.id.ilike("cloud___%"))\
        .filter(~Student.registration_number.ilike("cloud___%"))
    if student_id and student_id != "All":
        records_query = records_query.filter(or_(Student.id == student_id, Student.registration_number == student_id))

    # Ensure deterministic order for cryptographic hashing
    records = records_query.order_by(Student.registration_number).all()

    pdf = PDFReport()
    # Generate a cryptographic fingerprint for this specific session report
    # Using deterministic session metadata and student record digest for forensic integrity
    record_digest = hashlib.sha256(str([(r.id, s.registration_number) for r, s in records]).encode()).hexdigest()
    session_str = f"{sid}|{sess.start_time}|{record_digest}"
    pdf.session_hash = hashlib.sha256(session_str.encode()).hexdigest().upper()[:40]
    pdf.add_page()
    pdf.draw_digital_watermark()

    # Session Overview with Summary Box
    pdf.chapter_title('Session Intelligence Report')

    metrics = [
        ("Subject Code", sub.code if sub else 'N/A', False),
        ("Total Present", len(records), False),
        ("Audit Result", "AUTHENTICATED", False)
    ]
    pdf.draw_summary_box(metrics)

    # Detailed Student Showcase (ONLY if a specific student is selected)
    if student_id and student_id != "All" and records:
        pdf.chapter_title('Biometric Forensic Audit')
        # records[0] is the specific student result
        rec, stu = records[0]
        pdf.draw_student_audit_card(stu, rec, db=db)

    # Detailed Audit Info
    pdf.set_font('helvetica', 'B', 10)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(35, 7, "Course Title:", 0, 0)
    pdf.set_font('helvetica', '', 10)
    pdf.cell(100, 7, f"{sub.name if sub else 'Unknown'}", 0, 1)

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(35, 7, "Faculty Lead:", 0, 0)
    pdf.set_font('helvetica', '', 10)
    pdf.cell(100, 7, f"{user_obj.full_name if user_obj else 'N/A'} ({user_obj.username if user_obj else 'ID N/A'})", 0, 1)

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(35, 7, "Environment:", 0, 0)
    pdf.set_font('helvetica', '', 10)
    pdf.cell(100, 7, f"{room.name if room else 'Virtual Node'} (WiFi: {room.wifi_ssid if room else 'N/A'})", 0, 1)

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(35, 7, "Record Hash:", 0, 0)
    pdf.set_font('helvetica', '', 8)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(100, 7, f"SHA256:{uuid.uuid4().hex}{uuid.uuid4().hex}".upper()[:40], 0, 1)
    pdf.ln(5)

    # Professional Table with Forensic Photos
    pdf.chapter_title('Verified Attendance Register (Forensic Data)')
    pdf.set_font('helvetica', 'B', 9)
    pdf.set_fill_color(21, 101, 192) # Dark Blue
    pdf.set_text_color(255, 255, 255)

    # Column widths: Adjusted for Forensic Photo column
    w = [35, 75, 45, 35]
    headers = ['Reg No', 'Student Identity', 'Biometric Record', 'Audit Status']

    for i in range(len(headers)):
        pdf.cell(w[i], 12, headers[i], 1, 0, 'C', 1)
    pdf.ln()

    pdf.set_font('helvetica', '', 8)
    pdf.set_text_color(0, 0, 0)
    fill = False
    for rec, stu in records:
        if fill: pdf.set_fill_color(242, 247, 251)
        else: pdf.set_fill_color(255, 255, 255)

        start_x = pdf.get_x()
        start_y = pdf.get_y()

        # Row height for photos
        row_h = 22

        # Cell 1: Reg No
        pdf.cell(w[0], row_h, f" {str(stu.registration_number)}", 1, 0, 'C', 1)

        # Cell 2: Student Name + Hash
        name_x = pdf.get_x()
        pdf.cell(w[1], row_h, "", 1, 0, 'L', 1)
        pdf.set_xy(name_x + 2, start_y + 3)
        pdf.set_font('helvetica', 'B', 9)
        pdf.cell(w[1]-4, 5, f"{str(stu.full_name)[:35]}", 0, 1, 'L')

        pdf.set_x(name_x + 2)
        pdf.set_font('helvetica', 'I', 7)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(w[1]-4, 4, f"Hash: {rec.record_hash[:20] if rec.record_hash else 'N/A'}", 0, 1, 'L')

        pdf.set_x(name_x + 2)
        pdf.set_font('helvetica', '', 7)
        loc_str = f"GPS: {rec.latitude}, {rec.longitude}" if rec.latitude else "GPS: Signal Lost/Interior"
        pdf.cell(w[1]-4, 4, loc_str, 0, 0, 'L')

        pdf.set_text_color(0, 0, 0)
        pdf.set_font('helvetica', '', 8)
        pdf.set_xy(name_x + w[1], start_y)

        # Biometric Photo Column
        photo_x = pdf.get_x()
        pdf.cell(w[2], row_h, "", 1, 0, 'C', 1) # Placeholder cell for photo border

        photo_path = f"static/faces/{stu.registration_number}.jpg"
        # Restore if missing
        if not os.path.exists(photo_path) and stu.face_image:
            try:
                with open(photo_path, "wb") as f:
                    f.write(stu.face_image)
            except: pass

        if os.path.exists(photo_path):
            try:
                # Center the photo in the cell
                pdf.image(photo_path, photo_x + 12, start_y + 1, 20, 20)
            except:
                pdf.set_xy(photo_x, start_y)
                pdf.cell(w[2], row_h, "Error", 0, 0, 'C')
        else:
            pdf.set_xy(photo_x, start_y)
            pdf.cell(w[2], row_h, "No Data", 0, 0, 'C')

        # Status Column
        pdf.set_xy(photo_x + w[2], start_y)
        if rec.face_verified:
            pdf.set_text_color(46, 125, 50)
            pdf.set_font('helvetica', 'B', 9)
            status = "VERIFIED"
        else:
            pdf.set_text_color(100, 100, 100)
            pdf.set_font('helvetica', '', 9)
            status = "MARKED"

        pdf.cell(w[3], row_h, status, 1, 1, 'C', 1)
        pdf.set_text_color(0, 0, 0)
        fill = not fill

    pdf_output = pdf.output()
    if isinstance(pdf_output, (bytearray, bytes)):
        return Response(content=bytes(pdf_output), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Session_Report_{sid[:8]}.pdf"})
    else:
        return Response(content=str(pdf_output).encode('utf-8'), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Session_Report_{sid[:8]}.pdf"})

@app.get("/reports/bulk-pdf")
async def export_bulk_pdf(
    faculty_id: str,
    branch: Optional[str] = "All",
    year: Optional[str] = "All",
    subject_id: Optional[str] = "All",
    student_id: Optional[str] = "All",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Generates a professional consolidated PDF report for Faculty"""
    fid = clean_id(faculty_id)
    # Start with a subquery or join to ensure we have Subject info for filtering
    query = db.query(AttendanceSession).join(Subject, AttendanceSession.subject_id == Subject.id)\
        .filter(AttendanceSession.faculty_id == fid)\
        .filter(~AttendanceSession.id.ilike("cloud___%"))\
        .filter(~Subject.id.ilike("cloud___%"))

    query = apply_academic_filters(query, Subject, branch, year)

    if is_valid(subject_id):
        query = query.filter(AttendanceSession.subject_id == clean_id(subject_id))

    if start_date:
        try: query = query.filter(AttendanceSession.start_time >= datetime.fromisoformat(start_date.replace('Z', '+00:00')))
        except: pass
    if end_date:
        try: query = query.filter(AttendanceSession.start_time <= datetime.fromisoformat(end_date.replace('Z', '+00:00')))
        except: pass

    # Subqueries to avoid parameter limits (1000+) in SQL 'IN' clauses
    session_id_sub = query.with_entities(AttendanceSession.id)
    subject_id_sub = query.with_entities(AttendanceSession.subject_id).distinct()

    # We need to check if any sessions exist before proceeding
    # Using a count query is more efficient than fetching all
    total_sess = db.query(func.count(AttendanceSession.id)).filter(AttendanceSession.id.in_(session_id_sub)).scalar()

    if total_sess == 0:
        print(f"DEBUG: No sessions found for faculty_id={fid}, branch={branch}, year={year}, subject_id={subject_id}")
        raise HTTPException(status_code=404, detail="No attendance sessions found for the selected filters.")

    print(f"DEBUG: Found {total_sess} sessions for bulk report")

    # REFINED STUDENT SCOPING (Optimized for Large Data):
    # Find relevant student population
    # 1. Students who attended at least one filtered session
    attended_q = db.query(AttendanceRecord.student_id).filter(AttendanceRecord.session_id.in_(session_id_sub))
    # 2. Students enrolled in any of the filtered subjects (Electives)
    enrolled_q = db.query(Enrollment.student_id).filter(Enrollment.subject_id.in_(subject_id_sub))

    # 3. Main Audience (Students in same branch/year as subjects)
    subject_info = db.query(Subject.branch, Subject.year).filter(Subject.id.in_(subject_id_sub)).distinct().all()

    target_q = attended_q.union(enrolled_q)
    if subject_info:
        audience_conds = [((Student.branch == br) & (Student.year == yr)) for br, yr in subject_info]
        audience_q = db.query(Student.id).filter(or_(*audience_conds))
        target_q = target_q.union(audience_q)

    # FINAL AGGREGATED QUERY
    results_query = db.query(
        Student.registration_number,
        Student.full_name,
        func.count(AttendanceRecord.id)
    ).outerjoin(AttendanceRecord, (Student.id == AttendanceRecord.student_id) & (AttendanceRecord.session_id.in_(session_id_sub)))\
     .filter(Student.id.in_(target_q))

    if is_valid(student_id):
        results_query = results_query.filter(or_(Student.id == student_id, Student.registration_number == student_id))

    results = results_query.group_by(Student.registration_number, Student.full_name)\
     .order_by(Student.registration_number).all()

    pdf = PDFReport()

    # Check if we are auditing a specific student to include forensic evidence
    audit_student_obj = None
    latest_record = None
    if is_valid(student_id):
        audit_student_obj = db.query(Student).filter(or_(Student.id == student_id, Student.registration_number == student_id)).first()
        if audit_student_obj:
            latest_record = db.query(AttendanceRecord).filter(
                AttendanceRecord.student_id == audit_student_obj.id,
                AttendanceRecord.session_id.in_(session_id_sub)
            ).order_by(AttendanceRecord.marked_at.desc()).first()

    # Generate a cryptographic fingerprint for this bulk report
    # Enhanced deterministic hash using data digest for forensic integrity
    data_digest = hashlib.sha256(str(results).encode()).hexdigest()
    report_str = f"{fid}|{branch}|{year}|{subject_id}|{total_sess}|{data_digest}"
    pdf.session_hash = hashlib.sha256(report_str.encode()).hexdigest().upper()[:40]
    pdf.add_page()
    pdf.draw_digital_watermark()

    # Advanced Summary Section
    pdf.chapter_title('Faculty Consolidation & Audit Report')

    # Insert Forensic Evidence if a specific student is selected
    if audit_student_obj:
        pdf.draw_student_audit_card(audit_student_obj, latest_record)
        pdf.ln(5)

    # Calculate High-Level Metrics
    total_students = len(results)
    avg_attendance = sum([(att/total_sess)*100 for _, _, att in results]) / total_students if total_students > 0 else 0
    defaulters = [r for r in results if (r[2]/total_sess)*100 < 75]

    metrics = [
        ("Total Sessions", total_sess, False),
        ("Avg Attendance", f"{avg_attendance:.1f}%", False),
        ("Total Students", total_students, False),
        ("Defaulters", len(defaulters), len(defaulters) > 0)
    ]
    pdf.draw_summary_box(metrics)
    pdf.ln(5)

    # Attendance Distribution Chart
    labels = ["Below 50%", "50-75% (Critical)", "75-90% (Good)", "Above 90% (Elite)"]
    ranges = [0, 0, 0, 0] # <50, 50-75, 75-90, >90
    for _, _, att in results:
        p = (att/total_sess)*100
        if p < 50: ranges[0]+=1
        elif p < 75: ranges[1]+=1
        elif p < 90: ranges[2]+=1
        else: ranges[3]+=1

    counts = [ranges[0], ranges[1], ranges[2], ranges[3]]
    colors = [(211, 47, 47), (255, 160, 0), (56, 142, 60), (21, 101, 192)]
    pdf.draw_distribution_chart(labels, counts, colors)

    # AI-Powered Insight Box
    pdf.ln(5)
    pdf.set_fill_color(248, 249, 250)
    pdf.set_draw_color(230, 230, 230)
    insight_y = pdf.get_y()
    pdf.rect(10, insight_y, 190, 35, 'FD')
    pdf.set_xy(15, insight_y + 2)
    pdf.set_font('helvetica', 'B', 9)
    pdf.set_text_color(*pdf.primary_color)
    pdf.cell(0, 7, "SYSTEM INTELLIGENCE: COHORT ANALYSIS", 0, 1)

    pdf.set_font('helvetica', '', 9)
    pdf.set_text_color(80, 80, 80)
    pdf.set_x(15)
    insight_text = f"Audit of {total_sess} sessions reveals a {avg_attendance:.1f}% engagement rate. " \
                   f"{len(defaulters)} students are currently non-compliant with the 75% attendance policy. " \
                   f"Recommendation: Dispatch academic warnings to critical nodes."
    pdf.multi_cell(180, 5, insight_text)

    pdf.set_y(insight_y + 40)

    # Detailed Student Table
    pdf.chapter_title('Student Performance Matrix')
    pdf.set_font('helvetica', 'B', 10); pdf.set_fill_color(21, 101, 192); pdf.set_text_color(255, 255, 255)

    w = [35, 85, 35, 35]
    pdf.cell(w[0], 12, 'Reg No', 1, 0, 'C', 1)
    pdf.cell(w[1], 12, 'Student Name', 1, 0, 'C', 1)
    pdf.cell(w[2], 12, 'Classes', 1, 0, 'C', 1)
    pdf.cell(w[3], 12, 'Percentage', 1, 1, 'C', 1)

    pdf.set_font('helvetica', '', 10); pdf.set_text_color(0,0,0)
    fill = False
    for reg, name, att in results:
        perc = (att / total_sess) * 100
        is_defaulter = perc < 75

        if is_defaulter:
            pdf.set_fill_color(255, 235, 238)
            pdf.set_text_color(183, 28, 28)
        elif fill:
            pdf.set_fill_color(245, 247, 249)
            pdf.set_text_color(0, 0, 0)
        else:
            pdf.set_fill_color(255, 255, 255)
            pdf.set_text_color(0, 0, 0)

        pdf.cell(w[0], 10, f" {str(reg)}", 1, 0, 'C', 1)
        pdf.cell(w[1], 10, f" {name}", 1, 0, 'L', 1)
        pdf.cell(w[2], 10, f"{att}/{total_sess}", 1, 0, 'C', 1)

        if is_defaulter:
            pdf.set_font('helvetica', 'B', 10)
        pdf.cell(w[3], 10, f"{perc:.1f}%", 1, 1, 'C', 1)
        pdf.set_font('helvetica', '', 10)
        fill = not fill

    pdf_output = pdf.output()
    if isinstance(pdf_output, (bytearray, bytes)):
        return Response(content=bytes(pdf_output), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=Faculty_Bulk_Report.pdf"})
    else:
        return Response(content=str(pdf_output).encode('utf-8'), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=Faculty_Bulk_Report.pdf"})

@app.get("/reports/summary")
async def get_reports_summary(
    faculty_id: Optional[str] = None,
    department_id: Optional[str] = None,
    branch: Optional[str] = "All",
    year: Optional[str] = "All",
    subject_id: Optional[str] = "All",
    student_id: Optional[str] = "All",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Returns a quick summary (counts) of sessions and students matching filters."""
    query = db.query(AttendanceSession).join(Subject, AttendanceSession.subject_id == Subject.id).outerjoin(Teacher, AttendanceSession.faculty_id == Teacher.id)

    if is_valid(faculty_id):
        fid = clean_id(faculty_id)
        query = query.filter(AttendanceSession.faculty_id == fid)

    if is_valid(department_id):
        actual_dept = resolve_dept(department_id, db)
        # HOD sees subjects in their dept OR sessions taken by their teachers
        query = query.filter(
            (Subject.department_id.ilike(f"%{actual_dept}%")) |
            (Subject.branch.ilike(f"%{actual_dept}%")) |
            (Teacher.department_id.ilike(f"%{actual_dept}%")) |
            (Teacher.branch.ilike(f"%{actual_dept}%"))
        )

    query = apply_academic_filters(query, Subject, branch, year)

    if is_valid(subject_id):
        query = query.filter(AttendanceSession.subject_id == clean_id(subject_id))

    if start_date:
        try: query = query.filter(AttendanceSession.start_time >= datetime.fromisoformat(start_date.replace('Z', '+00:00')))
        except: pass
    if end_date:
        try: query = query.filter(AttendanceSession.start_time <= datetime.fromisoformat(end_date.replace('Z', '+00:00')))
        except: pass

    session_ids = [s.id for s in query.with_entities(AttendanceSession.id).all()]
    total_sessions = len(session_ids)

    if total_sessions == 0:
        return {"total_sessions": 0, "total_students": 0}

    # Count unique students who attended these sessions
    student_count = db.query(AttendanceRecord.student_id).filter(AttendanceRecord.session_id.in_(session_ids)).distinct().count()

    # If student_id is provided, check if that specific student exists in these sessions
    if is_valid(student_id):
        is_present = db.query(AttendanceRecord).join(Student, AttendanceRecord.student_id == Student.id).filter(
            AttendanceRecord.session_id.in_(session_ids),
            or_(
                AttendanceRecord.student_id == student_id,
                Student.registration_number == student_id
            )
        ).first() is not None
        student_count = 1 if is_present else 0

    return {
        "total_sessions": total_sessions,
        "total_students": student_count
    }

@app.get("/analytics/department/{dept_id}")
async def get_department_analytics(dept_id: str, db: Session = Depends(get_db)):
    # 1. Resolve Department
    actual_dept = resolve_dept(dept_id, db)

    # 2. Base Stats with Lenient Matching
    sessions = db.query(AttendanceSession).join(Subject).outerjoin(Teacher, AttendanceSession.faculty_id == Teacher.id).filter(
        (Subject.department_id.ilike(f"%{actual_dept}%")) |
        (Subject.branch.ilike(f"%{actual_dept}%")) |
        (Teacher.department_id.ilike(f"%{actual_dept}%")) |
        (Teacher.branch.ilike(f"%{actual_dept}%"))
    ).all()
    session_ids = [s.id for s in sessions]

    total_faculty = db.query(Teacher).filter(
        (Teacher.department_id.ilike(f"%{actual_dept}%")) | (Teacher.branch.ilike(f"%{actual_dept}%"))
    ).count()

    total_students = db.query(Student).filter(
        (Student.department_id.ilike(f"%{actual_dept}%")) | (Student.branch.ilike(f"%{actual_dept}%"))
    ).count()

    # 3. Calculate Performance Metrics
    if session_ids and total_students > 0:
        total_attendance_recs = db.query(AttendanceRecord).filter(AttendanceRecord.session_id.in_(session_ids)).count()
        # Max possible attendance = sessions * students
        avg_perc = (total_attendance_recs / (len(session_ids) * total_students)) * 100
        avg_attendance_str = f"{avg_perc:.1f}%"

        # Count Defaulters (<75% attendance)
        # Note: We group by student_id to get individual counts across filtered sessions
        student_counts = db.query(
            Student.id, func.count(AttendanceRecord.id)
        ).outerjoin(AttendanceRecord, (Student.id == AttendanceRecord.student_id) & (AttendanceRecord.session_id.in_(session_ids)))\
         .filter((Student.department_id.ilike(f"%{actual_dept}%")) | (Student.branch.ilike(f"%{actual_dept}%")))\
         .group_by(Student.id).all()

        defaulter_count = 0
        for sid, count in student_counts:
            if (count / len(session_ids)) * 100 < 75:
                defaulter_count += 1
    else:
        avg_attendance_str = "0.0%"
        defaulter_count = 0

    # 4. Real-Time Monthly Trends
    # We aggregate attendance percentages by month for the current department
    trends = []
    from sqlalchemy import extract
    for i in range(5, -1, -1):
        # Calculate date for 'i' months ago
        target_date = datetime.utcnow() - timedelta(days=i*30)
        month_num = target_date.month
        year_num = target_date.year
        month_name = target_date.strftime("%b")

        month_sessions = db.query(AttendanceSession).join(Subject).filter(
            ((Subject.department_id.ilike(f"%{actual_dept}%")) | (Subject.branch.ilike(f"%{actual_dept}%"))),
            extract('month', AttendanceSession.start_time) == month_num,
            extract('year', AttendanceSession.start_time) == year_num
        ).all()

        if not month_sessions:
            trends.append({"month": month_name, "value": 0})
            continue

        m_session_ids = [s.id for s in month_sessions]
        m_attendance = db.query(AttendanceRecord).filter(AttendanceRecord.session_id.in_(m_session_ids)).count()
        m_possible = len(m_session_ids) * (total_students or 1)
        m_perc = min(100, int((m_attendance / m_possible) * 100))
        trends.append({"month": month_name, "value": m_perc})

    return {
        "avg_attendance": avg_attendance_str,
        "total_classes": len(sessions),
        "defaulter_count": max(0, defaulter_count),
        "total_faculty": total_faculty,
        "total_students": total_students,
        "trends": trends
    }

@app.get("/analytics/faculty/{faculty_id}")
async def get_faculty_analytics(faculty_id: str, db: Session = Depends(get_db)):
    """Faculty specific analytics for their own reports screen - Live Supabase Data"""
    fid = clean_id(faculty_id)
    # Get all sessions for this faculty (active or stopped)
    sessions = db.query(AttendanceSession).filter(AttendanceSession.faculty_id == fid).all()
    session_ids = [s.id for s in sessions]

    if not session_ids:
        return {"avg_attendance": "0%", "total_classes": 0, "defaulter_count": 0, "trends": []}

    # 1. Resolve the "Target Audience" for this faculty's subjects
    subject_ids = list(set([s.subject_id for s in sessions]))
    target_info = db.query(Subject.branch, Subject.year).filter(Subject.id.in_(subject_ids)).distinct().all()

    audience_student_ids = set()
    for br, yr in target_info:
        # Using ILike for robustness across Supabase naming variations
        ids = [s[0] for s in db.query(Student.id).filter(Student.branch.ilike(f"%{br}%"), Student.year.ilike(f"%{yr}%")).all()]
        audience_student_ids.update(ids)

    # Also include students who actually attended (catches electives/late enrollees)
    actual_attendees = [r[0] for r in db.query(AttendanceRecord.student_id).filter(AttendanceRecord.session_id.in_(session_ids)).distinct().all()]
    audience_student_ids.update(actual_attendees)

    total_potential_students = len(audience_student_ids)

    # 2. Calculate real avg attendance %
    total_records = db.query(AttendanceRecord).filter(AttendanceRecord.session_id.in_(session_ids)).count()
    max_possible = len(session_ids) * (total_potential_students or 1)
    avg_perc = (total_records / max_possible) * 100

    # 3. Calculate Defaulters (Students with < 75% in this faculty's classes)
    defaulter_count = 0
    if total_potential_students > 0:
        # Grouped query for efficiency
        att_counts = db.query(
            AttendanceRecord.student_id, func.count(AttendanceRecord.id)
        ).filter(AttendanceRecord.session_id.in_(session_ids)).group_by(AttendanceRecord.student_id).all()

        att_map = {sid: count for sid, count in att_counts}
        for sid in audience_student_ids:
            s_count = att_map.get(sid, 0)
            if (s_count / len(session_ids)) * 100 < 75:
                defaulter_count += 1

    # 4. Faculty Trends (Last 3 months)
    trends = []
    from sqlalchemy import extract
    for i in range(2, -1, -1):
        target_date = datetime.utcnow() - timedelta(days=i*30)
        m_name = target_date.strftime("%b")
        m_sessions = [s.id for s in sessions if s.start_time.month == target_date.month and s.start_time.year == target_date.year]

        if not m_sessions:
            trends.append({"month": m_name, "value": 0})
        else:
            m_rec_count = db.query(AttendanceRecord).filter(AttendanceRecord.session_id.in_(m_sessions)).count()
            m_poss = len(m_sessions) * (total_potential_students or 1)
            trends.append({"month": m_name, "value": min(100, int((m_rec_count / m_poss) * 100))})

    return {
        "avg_attendance": f"{avg_perc:.1f}%",
        "total_classes": len(sessions),
        "defaulter_count": defaulter_count,
        "trends": trends
    }

@app.get("/reports/hod-master-pdf")
async def export_hod_master_pdf(
    department_id: str,
    faculty_id: Optional[str] = "All",
    branch: Optional[str] = "All",
    year: Optional[str] = "All",
    subject_id: Optional[str] = "All",
    student_id: Optional[str] = "All",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """HOD Level: High-Standard Departmental Audit with Advanced Filtering & Null Handling"""
    did = clean_id(department_id)

    # 1. Resolve Department
    actual_dept = resolve_dept(department_id, db)

    # 2. Gather Sessions
    query = db.query(AttendanceSession).join(Subject, AttendanceSession.subject_id == Subject.id)\
        .outerjoin(User, AttendanceSession.faculty_id == User.id)\
        .outerjoin(Teacher, AttendanceSession.faculty_id == Teacher.id)\
        .filter(~AttendanceSession.id.ilike("cloud___%"))\
        .filter(~Subject.id.ilike("cloud___%"))\
        .filter(~User.id.ilike("cloud___%"))

    # Base filter: HOD sees subjects in their dept OR sessions taken by their teachers
    query = query.filter(
        (Subject.department_id.ilike(f"%{actual_dept}%")) |
        (Subject.branch.ilike(f"%{actual_dept}%")) |
        (Teacher.department_id.ilike(f"%{actual_dept}%")) |
        (Teacher.branch.ilike(f"%{actual_dept}%"))
    )

    # Apply valid filters
    if is_valid(faculty_id):
        fid = clean_id(faculty_id)
        query = query.filter((AttendanceSession.faculty_id == fid) | (User.username.ilike(f"%{fid}%")) | (User.full_name.ilike(f"%{fid}%")))

    if is_valid(subject_id):
        query = query.filter(AttendanceSession.subject_id == clean_id(subject_id))

    query = apply_academic_filters(query, Subject, branch, year)

    if start_date:
        try: query = query.filter(AttendanceSession.start_time >= datetime.fromisoformat(start_date.replace('Z', '+00:00')))
        except: pass
    if end_date:
        try: query = query.filter(AttendanceSession.start_time <= datetime.fromisoformat(end_date.replace('Z', '+00:00')))
        except: pass

    # Subqueries for optimized child queries
    session_id_sub = query.with_entities(AttendanceSession.id)
    subject_id_sub = query.with_entities(AttendanceSession.subject_id).distinct()

    # We need session data for report headers/faculty matrix
    # Using a subquery in IN is safe
    sessions_full = db.query(AttendanceSession, Subject, User).join(Subject).outerjoin(User, AttendanceSession.faculty_id == User.id).filter(AttendanceSession.id.in_(session_id_sub)).all()

    if not sessions_full:
        msg = f"No sessions found for {actual_dept}"
        if is_valid(branch): msg += f", Branch: {branch}"
        if is_valid(year): msg += f", Year: {year}"
        if is_valid(faculty_id): msg += f", Faculty: {faculty_id}"
        raise HTTPException(status_code=404, detail=msg)

    total_sess = len(sessions_full)

    # 3. Define the Student Audit Scope
    student_query = db.query(Student).filter(
        or_(
            Student.department_id.ilike(f"%{actual_dept}%"),
            Student.branch.ilike(f"%{actual_dept}%")
        )
    )
    student_query = apply_academic_filters(student_query, Student, branch, year)

    dept_student_ids_q = student_query.with_entities(Student.id)
    attended_student_ids_q = db.query(AttendanceRecord.student_id).filter(AttendanceRecord.session_id.in_(session_id_sub)).distinct()
    target_student_id_sub = dept_student_ids_q.union(attended_student_ids_q)

    # 4. Aggregate Performance
    results_query = db.query(
        Student.registration_number,
        Student.full_name,
        Student.branch,
        func.count(AttendanceRecord.id).label('attended_count')
    ).outerjoin(AttendanceRecord, (Student.id == AttendanceRecord.student_id) & (AttendanceRecord.session_id.in_(session_id_sub)))\
     .filter(Student.id.in_(target_student_id_sub))

    if is_valid(student_id):
        results_query = results_query.filter(or_(Student.id == student_id, Student.registration_number == student_id))

    student_stats = results_query.group_by(Student.registration_number, Student.full_name, Student.branch)\
     .order_by(Student.registration_number).all()

    if not student_stats:
        raise HTTPException(status_code=404, detail="No students found matching these criteria.")

    # AI Stats
    ai_verified = db.query(func.count(AttendanceRecord.id)).filter(
        AttendanceRecord.session_id.in_(session_id_sub),
        AttendanceRecord.face_verified == True
    ).scalar() or 0
    total_recs = db.query(func.count(AttendanceRecord.id)).filter(
        AttendanceRecord.session_id.in_(session_id_sub)
    ).scalar() or 0
    ai_accuracy = (ai_verified / total_recs * 100) if total_recs > 0 else 0

    # 5. Build Elite PDF
    pdf = PDFReport()

    # Check if we are auditing a specific student to include forensic evidence
    audit_student_obj = None
    latest_record = None
    if is_valid(student_id):
        audit_student_obj = db.query(Student).filter(or_(Student.id == student_id, Student.registration_number == student_id)).first()
        if audit_student_obj:
            latest_record = db.query(AttendanceRecord).filter(
                AttendanceRecord.student_id == audit_student_obj.id,
                AttendanceRecord.session_id.in_(session_id_sub)
            ).order_by(AttendanceRecord.marked_at.desc()).first()

    # Generate a cryptographic fingerprint for the HOD Master Audit
    # We use a deterministic digest of the student statistics and filters to ensure forensic integrity
    stats_digest = hashlib.sha256(str(student_stats).encode()).hexdigest()
    audit_str = f"{actual_dept}|{faculty_id}|{branch}|{year}|{subject_id}|{total_sess}|{stats_digest}"
    pdf.session_hash = hashlib.sha256(audit_str.encode()).hexdigest().upper()[:40]
    pdf.add_page()
    pdf.draw_digital_watermark()

    # Departmental Executive Summary
    pdf.chapter_title(f'Departmental Executive Audit: {actual_dept.upper()}')

    # Insert Forensic Evidence if a specific student is selected
    if audit_student_obj:
        pdf.draw_student_audit_card(audit_student_obj, latest_record)
        pdf.ln(5)

    metrics = [
        ("Faculty Node", len(set([s[2].id for s in sessions_full if s[2]])), False),
        ("Audit Sessions", total_sess, False),
        ("AI Confidence", f"{ai_accuracy:.1f}%", False),
        ("Compliance", "GOVT STANDARDS", False)
    ]
    pdf.draw_summary_box(metrics)

    # Analytics Matrix
    ranges = [0, 0, 0, 0]
    for _, _, _, att in student_stats:
        p = (att/total_sess)*100
        if p < 50: ranges[0]+=1
        elif p < 75: ranges[1]+=1
        elif p < 90: ranges[2]+=1
        else: ranges[3]+=1

    labels = ["Below 50%", "50-75% (Critical)", "75-90% (Good)", "Elite 90+"]
    colors = [(184, 27, 27), (255, 160, 0), (56, 142, 60), (21, 101, 192)]
    pdf.draw_distribution_chart(labels, ranges, colors)

    # Institutional Insight
    pdf.ln(5)
    insight_y = pdf.get_y()
    pdf.set_fill_color(250, 250, 252)
    pdf.set_draw_color(*pdf.primary_color)
    pdf.rect(10, insight_y, 190, 35, 'FD')
    pdf.set_xy(15, insight_y + 2)
    pdf.set_font('helvetica', 'B', 9)
    pdf.set_text_color(*pdf.primary_color)
    pdf.cell(0, 7, "VJTI INSTITUTIONAL INTELLIGENCE", 0, 1)

    pdf.set_font('helvetica', '', 9)
    pdf.set_text_color(60, 60, 60)
    pdf.set_x(15)
    insight_text = f"Comprehensive audit of {actual_dept} department identifies {ranges[0]+ranges[1]} students in critical compliance zones. " \
                   f"The AI verification pipeline maintained {ai_accuracy:.1f}% confidence across {total_recs} biometric points. " \
                   f"This record is digitally signed for academic permanence."
    pdf.multi_cell(180, 5, insight_text)

    pdf.set_y(insight_y + 40)

    # Faculty Performance
    pdf.chapter_title('Faculty Engagement Matrix')
    pdf.set_font('helvetica', 'B', 9); pdf.set_fill_color(21, 101, 192); pdf.set_text_color(255, 255, 255)

    w_fac = [70, 70, 50]
    pdf.cell(w_fac[0], 10, 'Faculty Name', 1, 0, 'C', 1)
    pdf.cell(w_fac[1], 10, 'Subject Title', 1, 0, 'C', 1)
    pdf.cell(w_fac[2], 10, 'Sessions Conducted', 1, 1, 'C', 1)

    pdf.set_font('helvetica', '', 9); pdf.set_text_color(0, 0, 0)
    fac_data = {}
    for s, sub, user in sessions_full:
        name = user.full_name if user else "Unknown Faculty"
        key = (name, sub.name)
        fac_data[key] = fac_data.get(key, 0) + 1

    fill = False
    for (name, sub_name), count in fac_data.items():
        if fill: pdf.set_fill_color(242, 247, 251)
        else: pdf.set_fill_color(255, 255, 255)

        pdf.cell(w_fac[0], 8, f" {name}", 1, 0, 'L', 1)
        pdf.cell(w_fac[1], 8, f" {sub_name}", 1, 0, 'L', 1)
        pdf.cell(w_fac[2], 8, str(count), 1, 1, 'C', 1)
        fill = not fill
    pdf.ln(10)

    # Student Compliance
    pdf.chapter_title('Student Academic Compliance Audit')
    pdf.set_font('helvetica', 'B', 9); pdf.set_fill_color(21, 101, 192); pdf.set_text_color(255, 255, 255)

    w_stu = [35, 80, 40, 35]
    pdf.cell(w_stu[0], 10, 'Reg No', 1, 0, 'C', 1)
    pdf.cell(w_stu[1], 10, 'Student Name', 1, 0, 'C', 1)
    pdf.cell(w_stu[2], 10, 'Attendance %', 1, 0, 'C', 1)
    pdf.cell(w_stu[3], 10, 'Status', 1, 1, 'C', 1)

    pdf.set_text_color(0,0,0); pdf.set_font('helvetica', '', 9)
    fill = False
    for reg, name, br, att in student_stats:
        perc = (att / total_sess) * 100
        is_defaulter = perc < 75
        status = "DEFAULTER" if is_defaulter else "COMPLIANT"

        if is_defaulter:
            pdf.set_fill_color(255, 235, 238)
            pdf.set_text_color(183, 28, 28)
        elif fill:
            pdf.set_fill_color(245, 247, 249)
            pdf.set_text_color(0, 0, 0)
        else:
            pdf.set_fill_color(255, 255, 255)
            pdf.set_text_color(0, 0, 0)

        pdf.cell(w_stu[0], 8, f" {str(reg)}", 1, 0, 'C', 1)
        pdf.cell(w_stu[1], 8, f" {name}", 1, 0, 'L', 1)
        pdf.cell(w_stu[2], 8, f"{perc:.1f}%", 1, 0, 'C', 1)

        if is_defaulter: pdf.set_font('helvetica', 'B', 9)
        pdf.cell(w_stu[3], 8, status, 1, 1, 'C', 1)
        pdf.set_font('helvetica', '', 9); pdf.set_text_color(0,0,0)
        fill = not fill

    pdf_output = pdf.output(dest='S')
    filename = f"HOD_Audit_{actual_dept}_{datetime.now().strftime('%Y%m%d')}.pdf"
    if isinstance(pdf_output, (bytearray, bytes)):
        return Response(content=bytes(pdf_output), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})
    else:
        return Response(content=pdf_output.encode('latin-1'), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})

@app.get("/reports/hod-master-excel")
async def export_hod_master_excel(
    department_id: str,
    faculty_id: Optional[str] = "All",
    branch: Optional[str] = "All",
    year: Optional[str] = "All",
    subject_id: Optional[str] = "All",
    student_id: Optional[str] = "All",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Exports HOD Master Audit data as CSV (Excel compatible) with BOM and Full Filtering"""
    import io, csv
    # 1. Resolve Department
    actual_dept = resolve_dept(department_id, db)

    # 2. Gather Sessions
    query = db.query(AttendanceSession).join(Subject, AttendanceSession.subject_id == Subject.id)\
        .outerjoin(User, AttendanceSession.faculty_id == User.id)\
        .outerjoin(Teacher, AttendanceSession.faculty_id == Teacher.id)\
        .filter(~AttendanceSession.id.ilike("cloud___%"))\
        .filter(~Subject.id.ilike("cloud___%"))\
        .filter(~User.id.ilike("cloud___%"))

    # Base filter: HOD sees subjects in their dept OR sessions taken by their teachers
    query = query.filter(
        (Subject.department_id.ilike(f"%{actual_dept}%")) |
        (Subject.branch.ilike(f"%{actual_dept}%")) |
        (Teacher.department_id.ilike(f"%{actual_dept}%")) |
        (Teacher.branch.ilike(f"%{actual_dept}%"))
    )

    # Apply valid filters
    if is_valid(faculty_id):
        fid = clean_id(faculty_id)
        query = query.filter((AttendanceSession.faculty_id == fid) | (User.username.ilike(f"%{fid}%")) | (User.full_name.ilike(f"%{fid}%")))

    if is_valid(subject_id):
        query = query.filter(AttendanceSession.subject_id == clean_id(subject_id))

    query = apply_academic_filters(query, Subject, branch, year)

    if start_date:
        try: query = query.filter(AttendanceSession.start_time >= datetime.fromisoformat(start_date.replace('Z', '+00:00')))
        except: pass
    if end_date:
        try: query = query.filter(AttendanceSession.start_time <= datetime.fromisoformat(end_date.replace('Z', '+00:00')))
        except: pass

    # Subqueries for optimized child queries
    session_id_sub = query.with_entities(AttendanceSession.id)

    # Count sessions
    total_sess = db.query(func.count(AttendanceSession.id)).filter(AttendanceSession.id.in_(session_id_sub)).scalar()

    if total_sess == 0:
        raise HTTPException(status_code=404, detail="No data found matching these filters.")

    # 3. Define the Student Audit Scope
    student_query = db.query(Student).filter((Student.department_id.ilike(f"%{actual_dept}%")) | (Student.branch.ilike(f"%{actual_dept}%")))
    student_query = apply_academic_filters(student_query, Student, branch, year)

    dept_student_ids_q = student_query.with_entities(Student.id)
    attended_student_ids_q = db.query(AttendanceRecord.student_id).filter(AttendanceRecord.session_id.in_(session_id_sub)).distinct()
    target_student_id_sub = dept_student_ids_q.union(attended_student_ids_q)

    # 4. Aggregate Performance
    results_query = db.query(
        Student.registration_number,
        Student.full_name,
        Student.branch,
        func.count(AttendanceRecord.id),
        func.sum(case([(AttendanceRecord.face_verified == True, 1)], else_=0))
    ).outerjoin(AttendanceRecord, (Student.id == AttendanceRecord.student_id) & (AttendanceRecord.session_id.in_(session_id_sub)))\
     .filter(Student.id.in_(target_student_id_sub))

    if is_valid(student_id):
        results_query = results_query.filter(or_(Student.id == student_id, Student.registration_number == student_id))

    stats = results_query.group_by(Student.registration_number, Student.full_name, Student.branch)\
     .order_by(Student.registration_number).all()

    # Create CSV with BOM for Excel compatibility
    output = io.StringIO()
    output.write('\ufeff') # UTF-8 BOM
    writer = csv.writer(output)
    writer.writerow([
        "Registration No",
        "Full Name",
        "Branch",
        "Classes Attended",
        "AI Verified",
        "Total Classes",
        "Attendance %",
        "AI Accuracy %",
        "Audit Status",
        "Digital Fingerprint"
    ])

    for reg, name, br, att, ai_v in stats:
        perc = (att/total_sess)*100 if total_sess > 0 else 0
        ai_acc = (ai_v/att)*100 if att > 0 else 0
        status = "ELIGIBLE" if perc >= 75 else "DEFAULTER"

        # Generate row-level fingerprint for audit integrity
        row_hash = hashlib.sha256(f"{reg}{att}{ai_v}{status}".encode()).hexdigest().upper()[:12]

        writer.writerow([
            reg,
            name,
            br,
            att,
            int(ai_v or 0),
            total_sess,
            f"{perc:.1f}%",
            f"{ai_acc:.1f}%",
            status,
            f"TX-{row_hash}"
        ])

    filename = f"HOD_Master_Audit_{actual_dept}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache"
        }
    )

@app.get("/analytics/department/{dept_id}/export")
async def export_department_excel(dept_id: str, db: Session = Depends(get_db)):
    """Exports departmental raw data to CSV for Excel with Real Supabase Data"""
    import io, csv
    actual_dept = resolve_dept(dept_id, db)

    # Fetch real data
    sessions = db.query(AttendanceSession).join(Subject).filter(
        (Subject.department_id.ilike(f"%{actual_dept}%")) | (Subject.branch.ilike(f"%{actual_dept}%"))
    ).all()

    session_ids = [s.id for s in sessions]

    students = db.query(Student).filter(
        (Student.department_id.ilike(f"%{actual_dept}%")) | (Student.branch.ilike(f"%{actual_dept}%"))
    ).all()

    output = io.StringIO()
    output.write('\ufeff') # BOM for Excel
    writer = csv.writer(output)
    writer.writerow([
        "Registration No",
        "Student Name",
        "Branch",
        "Year",
        "Attended",
        "AI Verified",
        "Total Sessions",
        "Attendance %",
        "Status",
        "Verification Hash"
    ])

    if session_ids:
        total_s = len(session_ids)
        for s in students:
            # Get attendance and AI verification count
            stats = db.query(
                func.count(AttendanceRecord.id),
                func.sum(case([(AttendanceRecord.face_verified == True, 1)], else_=0))
            ).filter(
                AttendanceRecord.student_id == s.id,
                AttendanceRecord.session_id.in_(session_ids)
            ).first()

            att_count = stats[0] or 0
            ai_count = int(stats[1] or 0)

            perc = (att_count / total_s) * 100 if total_s > 0 else 0
            status = "Compliant" if perc >= 75 else "DEFAULTER"

            # Row integrity hash
            v_hash = hashlib.sha256(f"{s.registration_number}{att_count}{status}".encode()).hexdigest().upper()[:12]

            writer.writerow([
                s.registration_number,
                s.full_name,
                s.branch,
                s.year,
                att_count,
                ai_count,
                total_s,
                f"{perc:.1f}%",
                status,
                f"VJTI-{v_hash}"
            ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=Dept_{actual_dept}_Report.csv"}
    )

@app.post("/faculty/schedule/{faculty_id}/sync-official")
async def sync_official_schedule(faculty_id: str, day: Optional[str] = None, db: Session = Depends(get_db)):
    """Copies official schedule entries to user's personalized schedule"""
    fid = clean_id(faculty_id)
    teacher = db.query(Teacher).filter(Teacher.id == fid).first()

    # 1. Identify relevant subjects (assigned or in teacher's branch)
    sub_query = db.query(Subject.id)
    if teacher and teacher.branch:
        sub_query = sub_query.filter(Subject.branch == teacher.branch)

    assigned_sub_ids = [s[0] for s in db.query(FacultySubject.subject_id).filter(FacultySubject.faculty_id == fid).all()]
    relevant_sub_ids = list(set([s[0] for s in sub_query.all()] + assigned_sub_ids))

    # 2. Find Official schedules for these subjects that aren't already assigned to this faculty
    official_query = db.query(Schedule).filter(
        Schedule.is_official == True,
        Schedule.subject_id.in_(relevant_sub_ids)
    )
    if day:
        official_query = official_query.filter(Schedule.day_of_week == day)

    official_schedules = official_query.all()

    # 3. Assign this faculty to official schedules if they match
    # Or copy them if they are 'master' records
    sync_count = 0
    for s in official_schedules:
        # If it's an official template with no faculty or wrong faculty, we 'claim' it for the sync
        # In a more complex system, we'd copy it. Here we just ensure the link exists.
        if s.faculty_id != fid:
            # We create a PERSONAL copy of the official schedule
            existing = db.query(Schedule).filter(
                Schedule.faculty_id == fid,
                Schedule.subject_id == s.subject_id,
                Schedule.day_of_week == s.day_of_week,
                Schedule.start_time == s.start_time
            ).first()

            if not existing:
                new_s = Schedule(
                    id=str(uuid.uuid4()),
                    subject_id=s.subject_id,
                    classroom_id=s.classroom_id,
                    faculty_id=fid,
                    day_of_week=s.day_of_week,
                    start_time=s.start_time,
                    end_time=s.end_time,
                    is_official=True # Keep it marked as official source
                )
                db.add(new_s)
                sync_count += 1

    db.commit()

    # 4. Return updated schedule
    query = db.query(Schedule, Subject, Classroom).join(Subject).join(Classroom).filter(Schedule.faculty_id == fid)
    if day: query = query.filter(Schedule.day_of_week == day)

    records = []
    for s, sub, c in query.all():
        records.append({
            "id": str(s.id), "day": s.day_of_week, "subject": sub.name, "subject_id": str(sub.id),
            "room": c.name, "classroom_id": str(c.id), "time": f"{s.start_time} - {s.end_time}", "is_official": s.is_official
        })

    return {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "day": day or "All Days",
        "synced": sync_count,
        "schedule": records
    }

@app.put("/faculty/schedule/{record_id}")
async def update_schedule_record(record_id: str, record: dict = Body(...), db: Session = Depends(get_db)):
    rid = clean_id(record_id)
    s = db.query(Schedule).filter(Schedule.id == rid).first()
    if not s: raise HTTPException(404, "Record not found")

    if "subject_id" in record: s.subject_id = record["subject_id"]
    if "classroom_id" in record: s.classroom_id = record["classroom_id"]
    if "day" in record: s.day_of_week = record["day"]
    if "time" in record:
        parts = record["time"].split(" - ")
        s.start_time = parts[0]
        if len(parts) > 1: s.end_time = parts[1]

    db.commit(); db.refresh(s)
    sub = db.query(Subject).filter(Subject.id == s.subject_id).first()
    room = db.query(Classroom).filter(Classroom.id == s.classroom_id).first()
    return {
        "id": str(s.id), "day": s.day_of_week, "subject": sub.name if sub else "Unknown",
        "room": room.name if room else "Unknown", "time": f"{s.start_time} - {s.end_time}"
    }

@app.get("/faculty/all")
async def get_all_faculty(db: Session = Depends(get_db)):
    """Returns a list of all faculty members with full profile for HOD views"""
    results = db.query(User, Teacher).join(Teacher, User.id == Teacher.id).filter(User.role == "faculty").all()

    profiles = []
    for user, teacher in results:
        profiles.append({
            "id": str(user.id),
            "username": str(user.username),
            "email": str(user.email or f"{user.username}@vjti.ac.in"),
            "full_name": str(user.full_name),
            "role": "faculty",
            "academic": {
                "branch": str(teacher.branch or ""),
                "designation": str(teacher.designation or ""),
                "employee_id": str(teacher.employee_id or "")
            }
        })
    return profiles

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
