import os
import uuid
import random
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import Classroom, Base, DATABASE_URL

# Connect to database
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def generate_bssid():
    return ":".join(["{:02x}".format(random.randint(0, 255)) for _ in range(6)])

def get_classroom_list():
    # Exact names provided by user
    classes = [
        "CS-IT lab 2", "AL002", "AL003", "CS-IT lab-3", "CCF1", "Dept2", "Dep1",
        "Auditorium", "Blockchain Lab", "Structural Engineering lab",
        "Concrete Technology lab", "Fluid Mechanics lab", "Hydrology Lab",
        "Transportation Engineering lab", "Plumbing lab",
        "Construction and Maintance Activities Cell", "Internet Lab", "Textile Hall",
        "CL401"
    ]

    # Range: CL001 - CL010
    for i in range(1, 11):
        classes.append(f"CL{i:03d}")

    # Range: CL201 - CL210
    for i in range(201, 211):
        classes.append(f"CL{i}")

    # Range: CL301 - CL310
    for i in range(301, 311):
        classes.append(f"CL{i}")

    return list(set(classes))

def upload_classrooms():
    classroom_names = get_classroom_list()
    count = 0

    # Use a consistent SSID for the campus
    campus_ssid = "VJTI_Campus_WiFi"

    for name in classroom_names:
        exists = db.query(Classroom).filter(Classroom.name == name).first()
        if not exists:
            new_room = Classroom(
                id=str(uuid.uuid4()),
                name=name,
                wifi_ssid=campus_ssid,
                wifi_bssid=generate_bssid().upper()
            )
            db.add(new_room)
            count += 1

    db.commit()
    print(f"Successfully added {count} classrooms/labs to the database.")

if __name__ == "__main__":
    upload_classrooms()
