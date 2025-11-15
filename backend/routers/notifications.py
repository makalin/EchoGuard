"""
Notification management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import datetime

from backend.database import get_db
from backend.models import Alert, Detection
from backend.services.alert_service import AlertService

router = APIRouter()
alert_service = AlertService()


class NotificationConfig(BaseModel):
    email: Optional[EmailStr] = None
    webhook_url: Optional[str] = None
    sms_number: Optional[str] = None
    enabled: bool = True
    threat_types: List[str] = ["blast_fishing", "vessel", "seismic"]


class AlertResponse(BaseModel):
    id: int
    detection_id: int
    alert_type: str
    status: str
    message: Optional[str]
    sent_at: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True


@router.get("/alerts", response_model=List[AlertResponse])
async def list_alerts(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all alerts"""
    query = db.query(Alert)
    
    if status:
        query = query.filter(Alert.status == status)
    
    alerts = query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        AlertResponse(
            id=alert.id,
            detection_id=alert.detection_id,
            alert_type=alert.alert_type,
            status=alert.status,
            message=alert.message,
            sent_at=alert.sent_at.isoformat() if alert.sent_at else None,
            created_at=alert.created_at.isoformat()
        )
        for alert in alerts
    ]


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: int, db: Session = Depends(get_db)):
    """Get alert by ID"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return AlertResponse(
        id=alert.id,
        detection_id=alert.detection_id,
        alert_type=alert.alert_type,
        status=alert.status,
        message=alert.message,
        sent_at=alert.sent_at.isoformat() if alert.sent_at else None,
        created_at=alert.created_at.isoformat()
    )


@router.post("/alerts/{detection_id}/resend")
async def resend_alert(detection_id: int, db: Session = Depends(get_db)):
    """Resend alert for a detection"""
    detection = db.query(Detection).filter(Detection.id == detection_id).first()
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    if not detection.is_threat:
        raise HTTPException(status_code=400, detail="Detection is not a threat")
    
    try:
        await alert_service.send_alert(detection, db)
        return {"message": "Alert resent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resending alert: {str(e)}")


@router.get("/alerts/stats")
async def get_alert_stats(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get alert statistics"""
    from sqlalchemy import func
    from datetime import timedelta
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    total = db.query(func.count(Alert.id)).filter(
        Alert.created_at >= start_date
    ).scalar()
    
    sent = db.query(func.count(Alert.id)).filter(
        Alert.created_at >= start_date,
        Alert.status == "sent"
    ).scalar()
    
    failed = db.query(func.count(Alert.id)).filter(
        Alert.created_at >= start_date,
        Alert.status == "failed"
    ).scalar()
    
    pending = db.query(func.count(Alert.id)).filter(
        Alert.created_at >= start_date,
        Alert.status == "pending"
    ).scalar()
    
    # By alert type
    by_type = db.query(
        Alert.alert_type,
        func.count(Alert.id).label('count')
    ).filter(
        Alert.created_at >= start_date
    ).group_by(Alert.alert_type).all()
    
    return {
        "period_days": days,
        "total_alerts": total,
        "sent": sent,
        "failed": failed,
        "pending": pending,
        "success_rate": round((sent / total * 100) if total > 0 else 0, 2),
        "by_type": {alert_type: count for alert_type, count in by_type}
    }

