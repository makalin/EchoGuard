"""
Hydrophone management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from geoalchemy2.shape import to_shape

from backend.database import get_db
from backend.models import Hydrophone, Detection
from sqlalchemy import func


router = APIRouter()


class HydrophoneCreate(BaseModel):
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    depth: Optional[float] = None
    status: str = "active"


class HydrophoneUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    depth: Optional[float] = None
    status: Optional[str] = None


class HydrophoneResponse(BaseModel):
    id: int
    name: str
    latitude: Optional[float]
    longitude: Optional[float]
    depth: Optional[float]
    status: str
    created_at: str
    detection_count: Optional[int] = None
    
    class Config:
        from_attributes = True


@router.post("/", response_model=HydrophoneResponse)
async def create_hydrophone(
    hydrophone: HydrophoneCreate,
    db: Session = Depends(get_db)
):
    """Create a new hydrophone"""
    # Check if name already exists
    existing = db.query(Hydrophone).filter(Hydrophone.name == hydrophone.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Hydrophone with this name already exists")
    
    new_hydrophone = Hydrophone(
        name=hydrophone.name,
        latitude=hydrophone.latitude,
        longitude=hydrophone.longitude,
        depth=hydrophone.depth,
        status=hydrophone.status
    )
    
    db.add(new_hydrophone)
    db.commit()
    db.refresh(new_hydrophone)
    
    return HydrophoneResponse(
        id=new_hydrophone.id,
        name=new_hydrophone.name,
        latitude=new_hydrophone.latitude,
        longitude=new_hydrophone.longitude,
        depth=new_hydrophone.depth,
        status=new_hydrophone.status,
        created_at=new_hydrophone.created_at.isoformat()
    )


@router.get("/", response_model=List[HydrophoneResponse])
async def list_hydrophones(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all hydrophones"""
    query = db.query(Hydrophone)
    
    if status:
        query = query.filter(Hydrophone.status == status)
    
    hydrophones = query.all()
    
    # Get detection counts
    result = []
    for h in hydrophones:
        count = db.query(func.count(Detection.id)).filter(
            Detection.hydrophone_id == h.id
        ).scalar()
        
        result.append(HydrophoneResponse(
            id=h.id,
            name=h.name,
            latitude=h.latitude,
            longitude=h.longitude,
            depth=h.depth,
            status=h.status,
            created_at=h.created_at.isoformat(),
            detection_count=count
        ))
    
    return result


@router.get("/{hydrophone_id}", response_model=HydrophoneResponse)
async def get_hydrophone(hydrophone_id: int, db: Session = Depends(get_db)):
    """Get hydrophone by ID"""
    hydrophone = db.query(Hydrophone).filter(Hydrophone.id == hydrophone_id).first()
    if not hydrophone:
        raise HTTPException(status_code=404, detail="Hydrophone not found")
    
    count = db.query(func.count(Detection.id)).filter(
        Detection.hydrophone_id == hydrophone_id
    ).scalar()
    
    return HydrophoneResponse(
        id=hydrophone.id,
        name=hydrophone.name,
        latitude=hydrophone.latitude,
        longitude=hydrophone.longitude,
        depth=hydrophone.depth,
        status=hydrophone.status,
        created_at=hydrophone.created_at.isoformat(),
        detection_count=count
    )


@router.put("/{hydrophone_id}", response_model=HydrophoneResponse)
async def update_hydrophone(
    hydrophone_id: int,
    hydrophone_update: HydrophoneUpdate,
    db: Session = Depends(get_db)
):
    """Update hydrophone"""
    hydrophone = db.query(Hydrophone).filter(Hydrophone.id == hydrophone_id).first()
    if not hydrophone:
        raise HTTPException(status_code=404, detail="Hydrophone not found")
    
    # Update fields
    if hydrophone_update.name is not None:
        # Check name uniqueness
        existing = db.query(Hydrophone).filter(
            Hydrophone.name == hydrophone_update.name,
            Hydrophone.id != hydrophone_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Hydrophone with this name already exists")
        hydrophone.name = hydrophone_update.name
    
    if hydrophone_update.latitude is not None:
        hydrophone.latitude = hydrophone_update.latitude
    if hydrophone_update.longitude is not None:
        hydrophone.longitude = hydrophone_update.longitude
    if hydrophone_update.depth is not None:
        hydrophone.depth = hydrophone_update.depth
    if hydrophone_update.status is not None:
        hydrophone.status = hydrophone_update.status
    
    db.commit()
    db.refresh(hydrophone)
    
    count = db.query(func.count(Detection.id)).filter(
        Detection.hydrophone_id == hydrophone_id
    ).scalar()
    
    return HydrophoneResponse(
        id=hydrophone.id,
        name=hydrophone.name,
        latitude=hydrophone.latitude,
        longitude=hydrophone.longitude,
        depth=hydrophone.depth,
        status=hydrophone.status,
        created_at=hydrophone.created_at.isoformat(),
        detection_count=count
    )


@router.delete("/{hydrophone_id}")
async def delete_hydrophone(hydrophone_id: int, db: Session = Depends(get_db)):
    """Delete hydrophone"""
    hydrophone = db.query(Hydrophone).filter(Hydrophone.id == hydrophone_id).first()
    if not hydrophone:
        raise HTTPException(status_code=404, detail="Hydrophone not found")
    
    # Check if hydrophone has detections
    count = db.query(func.count(Detection.id)).filter(
        Detection.hydrophone_id == hydrophone_id
    ).scalar()
    
    if count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete hydrophone with {count} associated detections"
        )
    
    db.delete(hydrophone)
    db.commit()
    
    return {"message": "Hydrophone deleted successfully"}


@router.get("/{hydrophone_id}/statistics")
async def get_hydrophone_statistics(
    hydrophone_id: int,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get statistics for a specific hydrophone"""
    from datetime import datetime, timedelta
    
    hydrophone = db.query(Hydrophone).filter(Hydrophone.id == hydrophone_id).first()
    if not hydrophone:
        raise HTTPException(status_code=404, detail="Hydrophone not found")
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total detections
    total = db.query(func.count(Detection.id)).filter(
        Detection.hydrophone_id == hydrophone_id,
        Detection.timestamp >= start_date
    ).scalar()
    
    # Threat detections
    threats = db.query(func.count(Detection.id)).filter(
        Detection.hydrophone_id == hydrophone_id,
        Detection.timestamp >= start_date,
        Detection.is_threat == True
    ).scalar()
    
    # By event type
    event_types = db.query(
        Detection.event_type,
        func.count(Detection.id).label('count')
    ).filter(
        Detection.hydrophone_id == hydrophone_id,
        Detection.timestamp >= start_date
    ).group_by(Detection.event_type).all()
    
    return {
        "hydrophone_id": hydrophone_id,
        "hydrophone_name": hydrophone.name,
        "period_days": days,
        "total_detections": total,
        "threat_detections": threats,
        "by_event_type": {et: count for et, count in event_types}
    }

