"""
Initialize database with sample data
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.database import SessionLocal, engine, Base
from backend.models import Hydrophone, Detection
from datetime import datetime, timedelta
import random

# Create tables
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # Create sample hydrophones
    hydrophones = [
        Hydrophone(
            name="Pacific Station Alpha",
            latitude=37.7749,
            longitude=-122.4194,
            depth=150.0,
            status="active"
        ),
        Hydrophone(
            name="Atlantic Station Beta",
            latitude=40.7128,
            longitude=-74.0060,
            depth=200.0,
            status="active"
        ),
        Hydrophone(
            name="Indian Ocean Station Gamma",
            latitude=-33.8688,
            longitude=151.2093,
            depth=180.0,
            status="active"
        ),
    ]
    
    for h in hydrophones:
        existing = db.query(Hydrophone).filter(Hydrophone.name == h.name).first()
        if not existing:
            db.add(h)
    
    db.commit()
    print("Database initialized successfully!")
    
except Exception as e:
    print(f"Error initializing database: {e}")
    db.rollback()
finally:
    db.close()

