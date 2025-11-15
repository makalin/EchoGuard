"""
Dashboard data endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import List, Dict

from backend.database import get_db
from backend.models import Detection, Hydrophone

router = APIRouter()


@router.get("/map-data")
async def get_map_data(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get detection data for map visualization"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    detections = db.query(Detection).filter(
        and_(
            Detection.timestamp >= start_date,
            Detection.latitude.isnot(None),
            Detection.longitude.isnot(None)
        )
    ).all()
    
    map_data = []
    for det in detections:
        map_data.append({
            "id": det.id,
            "type": det.event_type,
            "is_threat": det.is_threat,
            "confidence": det.confidence,
            "latitude": det.latitude,
            "longitude": det.longitude,
            "timestamp": det.timestamp.isoformat()
        })
    
    return {"detections": map_data}


@router.get("/timeline")
async def get_timeline(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get detection timeline data"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Group by hour
    timeline = db.query(
        func.date_trunc('hour', Detection.timestamp).label('hour'),
        Detection.event_type,
        func.count(Detection.id).label('count')
    ).filter(
        Detection.timestamp >= start_date
    ).group_by(
        func.date_trunc('hour', Detection.timestamp),
        Detection.event_type
    ).order_by('hour').all()
    
    result = {}
    for hour, event_type, count in timeline:
        hour_str = hour.isoformat()
        if hour_str not in result:
            result[hour_str] = {}
        result[hour_str][event_type] = count
    
    return {"timeline": result}


@router.get("/hydrophones")
async def get_hydrophones(db: Session = Depends(get_db)):
    """Get all hydrophone locations"""
    hydrophones = db.query(Hydrophone).filter(Hydrophone.status == "active").all()
    
    return {
        "hydrophones": [
            {
                "id": h.id,
                "name": h.name,
                "latitude": h.latitude,
                "longitude": h.longitude,
                "depth": h.depth,
                "status": h.status
            }
            for h in hydrophones
        ]
    }

