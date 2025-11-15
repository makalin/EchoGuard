"""
Detection endpoints
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel

from backend.database import get_db
from backend.models import Detection, Hydrophone

router = APIRouter()


class DetectionResponse(BaseModel):
    id: int
    event_type: str
    confidence: float
    timestamp: datetime
    is_threat: bool
    latitude: Optional[float]
    longitude: Optional[float]
    hydrophone_id: Optional[int]
    hydrophone_name: Optional[str]
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[DetectionResponse])
async def get_detections(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    event_type: Optional[str] = None,
    is_threat: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    hydrophone_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get list of detections with filters"""
    query = db.query(Detection)
    
    # Apply filters
    if event_type:
        query = query.filter(Detection.event_type == event_type)
    if is_threat is not None:
        query = query.filter(Detection.is_threat == is_threat)
    if start_date:
        query = query.filter(Detection.timestamp >= start_date)
    if end_date:
        query = query.filter(Detection.timestamp <= end_date)
    if hydrophone_id:
        query = query.filter(Detection.hydrophone_id == hydrophone_id)
    
    # Order by timestamp descending
    detections = query.order_by(desc(Detection.timestamp)).offset(skip).limit(limit).all()
    
    # Format response
    results = []
    for det in detections:
        hydrophone_name = None
        if det.hydrophone:
            hydrophone_name = det.hydrophone.name
        
        results.append(DetectionResponse(
            id=det.id,
            event_type=det.event_type,
            confidence=det.confidence,
            timestamp=det.timestamp,
            is_threat=det.is_threat,
            latitude=det.latitude,
            longitude=det.longitude,
            hydrophone_id=det.hydrophone_id,
            hydrophone_name=hydrophone_name
        ))
    
    return results


@router.get("/{detection_id}", response_model=DetectionResponse)
async def get_detection(detection_id: int, db: Session = Depends(get_db)):
    """Get single detection by ID"""
    detection = db.query(Detection).filter(Detection.id == detection_id).first()
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    hydrophone_name = None
    if detection.hydrophone:
        hydrophone_name = detection.hydrophone.name
    
    return DetectionResponse(
        id=detection.id,
        event_type=detection.event_type,
        confidence=detection.confidence,
        timestamp=detection.timestamp,
        is_threat=detection.is_threat,
        latitude=detection.latitude,
        longitude=detection.longitude,
        hydrophone_id=detection.hydrophone_id,
        hydrophone_name=hydrophone_name
    )


@router.get("/stats/summary")
async def get_detection_stats(
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get detection statistics"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    total = db.query(Detection).filter(Detection.timestamp >= start_date).count()
    threats = db.query(Detection).filter(
        and_(Detection.timestamp >= start_date, Detection.is_threat == True)
    ).count()
    
    # Count by event type
    event_types = db.query(Detection.event_type, db.func.count(Detection.id)).filter(
        Detection.timestamp >= start_date
    ).group_by(Detection.event_type).all()
    
    return {
        "period_days": days,
        "total_detections": total,
        "threat_detections": threats,
        "non_threat_detections": total - threats,
        "by_event_type": {et: count for et, count in event_types}
    }

