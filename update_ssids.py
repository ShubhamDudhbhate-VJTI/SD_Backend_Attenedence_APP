import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import Classroom, DATABASE_URL

# Connect to database
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def update_ssids():
    rooms = db.query(Classroom).all()
    for room in rooms:
        # Setting all SSIDs to "Phone" as requested (case sensitive)
        room.wifi_ssid = "Phone"
        room.wifi_bssid = "00:00:00:00:00:00"

    db.commit()
    print(f"SUCCESS: Updated {len(rooms)} classrooms with SSID: 'Phone'")

if __name__ == "__main__":
    update_ssids()
