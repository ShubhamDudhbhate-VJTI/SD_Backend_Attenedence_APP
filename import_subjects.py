import os
import uuid
from sqlalchemy import create_engine, text
from main import DATABASE_URL

# Branch Mapping (Based on VJTI Department IDs)
DEPT_MAP = {
    "1": "Computer Engineering",
    "2": "Information Technology",
    "3": "Electronics Engineering",
    "4": "EXTC Engineering",
    "5": "Electrical Engineering",
    "6": "Mechanical Engineering",
    "7": "Civil Engineering",
    "8": "Production Engineering",
    "9": "Textile Engineering"
}

# Curriculum Data (NEP R5) - All 4 Years
CURRICULUM = {
    "2": { # IT
        "First Year": ["Engineering Maths", "Physics", "Chemistry", "Programming for Problem Solving (C)", "Engineering Mechanics", "Basic Electrical & Electronics"],
        "Second Year": ["Discrete Mathematics", "Data Structures & Algorithms", "Operating Systems", "DBMS", "Computer Organization", "Theory of Computation"],
        "Third Year": ["Artificial Intelligence", "Software Engineering", "Computer Networks", "Machine Learning", "Compiler Design", "Parallel Computing"],
        "Fourth Year": ["Cloud Computing (PE)", "Cyber Security (PE)", "Big Data (PE)", "Major Capstone Project"]
    },
    "1": { # CS
        "First Year": ["Engineering Maths", "Physics", "Chemistry", "Programming for Problem Solving (C)", "Engineering Mechanics", "Basic Electrical & Electronics"],
        "Second Year": ["Digital Logic Design", "Discrete Structures", "Data Structures", "COA", "Microprocessors"],
        "Third Year": ["System Programming", "Database Systems", "Computer Networks", "Algorithms", "AI & Robotics"],
        "Fourth Year": ["Deep Learning (PE)", "Blockchain (PE)", "Distributed Systems", "Major Capstone Project"]
    },
    "4": { # EXTC
        "First Year": ["Engineering Maths", "Physics", "Chemistry", "Programming for Problem Solving (C)", "Engineering Mechanics", "Basic Electrical & Electronics"],
        "Second Year": ["Electronic Devices & Circuits", "Network Theory", "Digital System Design", "Signals & Systems", "Control Systems"],
        "Third Year": ["Electromagnetic Engineering", "Microcontrollers", "Digital Communication", "Linear Integrated Circuits", "Antenna & Wave Propagation"],
        "Fourth Year": ["Optical Communication", "Embedded Systems", "VLSI Design", "Satellite Communication", "Major Capstone Project"]
    },
    "5": { # Electrical
        "First Year": ["Engineering Maths", "Physics", "Chemistry", "Programming for Problem Solving (C)", "Engineering Mechanics", "Basic Electrical & Electronics"],
        "Second Year": ["Electrical Machines-I", "Network Analysis", "Analog & Digital Electronics", "Electrical Measurements"],
        "Third Year": ["Power Systems", "Control Systems", "Power Electronics", "Electrical Machine Design", "Microprocessors"],
        "Fourth Year": ["High Voltage Engineering", "Switchgear & Protection", "Renewable Energy", "Power System Operation & Control", "Major Capstone Project"]
    },
    "6": { # Mechanical
        "First Year": ["Engineering Maths", "Physics", "Chemistry", "Programming for Problem Solving (C)", "Engineering Mechanics", "Basic Electrical & Electronics"],
        "Second Year": ["Thermodynamics", "Materials Science", "Strength of Materials", "Manufacturing Processes", "Kinematics of Machinery"],
        "Third Year": ["Heat Transfer", "Machine Design", "Fluid Mechanics", "Dynamics of Machinery", "Mechatronics"],
        "Fourth Year": ["CAD/CAM", "Refrigeration & Air Conditioning", "Internal Combustion Engines", "Industrial Engineering", "Major Capstone Project"]
    },
    "7": { # Civil
        "First Year": ["Engineering Maths", "Physics", "Chemistry", "Programming for Problem Solving (C)", "Engineering Mechanics", "Basic Electrical & Electronics"],
        "Second Year": ["Surveying", "Fluid Mechanics", "Strength of Materials", "Building Construction", "Engineering Geology"],
        "Third Year": ["Structural Analysis", "Geotechnical Engineering", "Environmental Engineering", "Transportation Engineering", "Hydrology"],
        "Fourth Year": ["Design of Steel Structures", "Concrete Technology", "Construction Management", "Irrigation Engineering", "Major Capstone Project"]
    },
    "8": { # Production
        "First Year": ["Engineering Maths", "Physics", "Chemistry", "Programming for Problem Solving (C)", "Engineering Mechanics", "Basic Electrical & Electronics"],
        "Second Year": ["Industrial Engineering", "Operations Research", "Quality Control", "Manufacturing Systems"],
        "Third Year": ["Tool Design", "Supply Chain Management", "Automation", "Lean Manufacturing"],
        "Fourth Year": ["Project Management", "Sustainable Manufacturing", "Industry 4.0", "Major Capstone Project"]
    },
    "9": { # Textile
        "First Year": ["Engineering Maths", "Physics", "Chemistry", "Programming for Problem Solving (C)", "Engineering Mechanics", "Basic Electrical & Electronics"],
        "Second Year": ["Fiber Science", "Spinning Technology", "Weaving Technology", "Textile Chemical Processing"],
        "Third Year": ["Knitting Technology", "Garment Manufacturing", "Testing & Quality Control", "Textile Design"],
        "Fourth Year": ["Technical Textiles", "Smart Textiles", "Textile Management", "Major Capstone Project"]
    }
}

def import_full_curriculum():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("Emptying existing Subject Data for a fresh start...")
        conn.execute(text("TRUNCATE TABLE branch_subjects, subjects CASCADE"))

        print("Importing FULL VJTI Curriculum (R5)...")

        for dept_id, years in CURRICULUM.items():
            branch_name = DEPT_MAP.get(dept_id, "Unknown")
            print(f"Processing: {branch_name}")

            for year_name, subjects in years.items():
                for sub_name in subjects:
                    # 1. Add to subjects table
                    sub_id = str(uuid.uuid4())
                    conn.execute(text("""
                        INSERT INTO subjects (id, name, branch, year, department_id)
                        VALUES (:id, :name, :branch, :year, :dept_id)
                    """), {
                        "id": sub_id,
                        "name": sub_name,
                        "branch": branch_name,
                        "year": year_name,
                        "dept_id": dept_id
                    })

                    # 2. Add to branch_subjects mapping
                    mapping_id = str(uuid.uuid4())
                    conn.execute(text("""
                        INSERT INTO branch_subjects (id, branch, year, subject_id)
                        VALUES (:id, :branch, :year, :sub_id)
                    """), {
                        "id": mapping_id,
                        "branch": branch_name,
                        "year": year_name,
                        "sub_id": sub_id
                    })

        conn.commit()
        print("\nSUCCESS: Entire 4-Year VJTI Curriculum (R5) imported successfully!")

if __name__ == "__main__":
    import_full_curriculum()
