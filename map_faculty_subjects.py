import os
import uuid
from sqlalchemy import create_engine, text
from main import DATABASE_URL

# Key Faculty to Subject Specialization Mapping
FACULTY_MAPPING = {
    "Dr. V. B. Nikam": ["DBMS", "Data Mining", "Advanced Databases"],
    "Prof. Sneha Pande": ["Web Technologies", "Full Stack", "MIS Development"],
    "Prof. S. T. Shingade": ["Discrete Mathematics", "Theory of Computation", "Engineering Maths"],
    "Dr. M. M. Chandane": ["Operating Systems", "Computer Networks"],
    "Dr. M. R. Shirole": ["IT Infrastructure", "System Security"],
    "Prof. P. M. Chavan": ["Software Engineering", "Cyber Security"],
    "Dr. Neha Singh": ["Computer Vision", "Image Processing"],
    "Prof. Swati Chopade": ["Java Programming", "Mobile App Development"],
    "Dr. R. A. Patil": ["Basic Electronics", "Electronic Devices", "Basic Electrical & Electronics"],
    "Dr. Faruk A. S. Kazi": ["Control Systems", "Smart Grids", "AI in Power"],
    "Dr. R. N. Awale": ["DSP", "VLSI Design", "Microelectronics"],
    "Dr. Sushma Wagh": ["Network Analysis", "Power System Stability"],
    "Dr. Neha Mishra": ["VLSI & Embedded Systems"],
    "Dr. Pragati Gupta": ["Microprocessors", "Embedded Control"],
    "Dr. G. M. Galshetwar": ["Basic Communication", "Analog/Digital Comm"],
    "Dr. Sachin S. Naik": ["Machine Design", "Mechanical Vibrations"],
    "Dr. N. P. Gulhane": ["Thermodynamics", "Heat Transfer", "Thermal Science"],
    "Dr. V. M. Phalle": ["Kinematics of Machinery", "Tribology"],
    "Dr. S. A. Mastud": ["Manufacturing Processes", "3D Printing", "CAD/CAM"],
    "Dr. A. V. Deshpande": ["Fluid Mechanics", "CFD"],
    "Dr. Mhaske S.Y.": ["Surveying", "Geospatial Technology"],
    "Dr. K. K. Sangle": ["Structural Analysis", "Matrix Methods"],
    "Dr. Wayal A.S.": ["Water Resource Engineering", "Hydrology"],
    "Dr. A. N. Bambole": ["Strength of Materials", "Design of Steel"],
    "Dr. Sayyad Sameer U.": ["Environmental Engineering", "Waste Management"],
    "Dr. D. N. Raut": ["Operations Research", "Project Management"],
    "Dr. M. R. Nagare": ["Machine Tools", "Industrial Engineering"],
    "Dr. D. K. Shinde": ["Nano-Engineering", "Design Engineering"],
    "Dr. P. R. Attar": ["Production Processes", "Metallurgy"],
    "Prof. Tushar More": ["Physics"],
    "Dr. D. S. Wavhal": ["Physics"],
    "Dr. Sujata Parameshwaran": ["Chemistry"],
    "Dr. Reena Pant": ["Mathematics"]
}

def map_faculty():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("Clearing existing faculty mappings...")
        conn.execute(text("TRUNCATE TABLE faculty_subjects"))

        # 1. Map Explicitly Listed Faculty
        print("Mapping specific faculty to their specializations...")
        for faculty_name, subjects in FACULTY_MAPPING.items():
            # Find User ID (Fuzzy match)
            # Remove dots and spaces for better matching
            clean_name = faculty_name.replace(".", "").replace(" ", "").lower()

            # Query the user
            user_res = conn.execute(text("SELECT id, full_name FROM app_users WHERE REPLACE(REPLACE(full_name, '.', ''), ' ', '') ILIKE :name"),
                                    {"name": f"%{clean_name}%"}).fetchone()

            if user_res:
                faculty_id = user_res[0]
                print(f"Mapping {user_res[1]}...")
                for sub_name in subjects:
                    # Find Subject ID
                    sub_res = conn.execute(text("SELECT id FROM subjects WHERE name ILIKE :sub"), {"sub": f"%{sub_name}%"}).fetchone()
                    if sub_res:
                        sub_id = sub_res[0]
                        mapping_id = str(uuid.uuid4())
                        conn.execute(text("INSERT INTO faculty_subjects (id, faculty_id, subject_id) VALUES (:id, :fid, :sid) ON CONFLICT DO NOTHING"),
                                     {"id": mapping_id, "fid": faculty_id, "sid": sub_id})
            else:
                print(f"Faculty Not Found: {faculty_name}")

        # 2. Assign remaining subjects randomly but department-wise
        print("\nFilling in remaining subjects department-wise...")
        subjects_res = conn.execute(text("SELECT id, name, department_id FROM subjects WHERE id NOT IN (SELECT subject_id FROM faculty_subjects)")).fetchall()

        for sub in subjects_res:
            sid, sname, dept_id = sub
            # Find a faculty in the same department
            faculty_in_dept = conn.execute(text("""
                SELECT u.id FROM app_users u
                JOIN app_teachers t ON u.id = t.id
                WHERE t.department_id = :dept_id LIMIT 1
            """), {"dept_id": dept_id}).fetchone()

            if faculty_in_dept:
                mapping_id = str(uuid.uuid4())
                conn.execute(text("INSERT INTO faculty_subjects (id, faculty_id, subject_id) VALUES (:id, :fid, :sid)"),
                             {"id": mapping_id, "fid": faculty_in_dept[0], "sid": sid})

        conn.commit()
        print("SUCCESS: Faculty-Subject mappings complete!")

if __name__ == "__main__":
    map_faculty()
