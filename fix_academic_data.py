import os
from sqlalchemy import create_engine, text
from main import DATABASE_URL

def fix_data():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("Standardizing Academic Data...")

        # Update Year names to match "First Year", "Second Year", etc.
        year_fixes = {
            "1st Year": "First Year",
            "2nd Year": "Second Year",
            "3rd Year": "Third Year",
            "4th Year": "Fourth Year",
            "1": "First Year",
            "2": "Second Year",
            "3": "Third Year",
            "4": "Fourth Year"
        }

        for old, new in year_fixes.items():
            conn.execute(text("UPDATE app_students SET year = :new WHERE year = :old"), {"new": new, "old": old})
            conn.execute(text("UPDATE subjects SET year = :new WHERE year = :old"), {"new": new, "old": old})

        # Standardize Branch names
        branch_fixes = {
            "IT": "Information Technology",
            "CS": "Computer Engineering",
            "CSE": "Computer Engineering",
            "EXTC": "EXTC Engineering",
            "MECH": "Mechanical Engineering",
            "CIVIL": "Civil Engineering"
        }

        for old, new in branch_fixes.items():
            conn.execute(text("UPDATE app_students SET branch = :new WHERE branch = :old"), {"new": new, "old": old})
            conn.execute(text("UPDATE subjects SET branch = :new WHERE branch = :old"), {"new": new, "old": old})

        conn.commit()
        print("Data Standardized successfully!")

if __name__ == "__main__":
    fix_data()
