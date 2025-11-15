"""
Analytics and statistics endpoints
"""
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from datetime import datetime, timedelta
from typing import Dict, List, Any

from backend.database import get_db
from backend.models import Detection, Hydrophone

router = APIRouter()


@router.get("/trends")
async def get_detection_trends(
    days: int = Query(30, ge=1, le=365),
    group_by: str = Query("day", regex="^(hour|day|week|month)$"),
    db: Session = Depends(get_db)
):
    """Get detection trends over time"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Determine grouping function
    if group_by == "hour":
        group_func = func.date_trunc('hour', Detection.timestamp)
    elif group_by == "day":
        group_func = func.date_trunc('day', Detection.timestamp)
    elif group_by == "week":
        group_func = func.date_trunc('week', Detection.timestamp)
    else:  # month
        group_func = func.date_trunc('month', Detection.timestamp)
    
    # Get trends
    trends = db.query(
        group_func.label('period'),
        Detection.event_type,
        func.count(Detection.id).label('count')
    ).filter(
        Detection.timestamp >= start_date
    ).group_by(
        group_func,
        Detection.event_type
    ).order_by('period').all()
    
    # Format results
    result = {}
    for period, event_type, count in trends:
        period_str = period.isoformat()
        if period_str not in result:
            result[period_str] = {}
        result[period_str][event_type] = count
    
    return {
        "group_by": group_by,
        "period_days": days,
        "trends": result
    }


@router.get("/heatmap")
async def get_detection_heatmap(
    days: int = Query(7, ge=1, le=365),
    resolution: float = Query(0.1, ge=0.01, le=1.0),
    db: Session = Depends(get_db)
):
    """Get detection heatmap data (geospatial clustering)"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    detections = db.query(Detection).filter(
        and_(
            Detection.timestamp >= start_date,
            Detection.latitude.isnot(None),
            Detection.longitude.isnot(None)
        )
    ).all()
    
    # Simple grid-based clustering
    heatmap_data = {}
    for det in detections:
        # Round to grid
        lat_grid = round(det.latitude / resolution) * resolution
        lon_grid = round(det.longitude / resolution) * resolution
        key = f"{lat_grid:.4f},{lon_grid:.4f}"
        
        if key not in heatmap_data:
            heatmap_data[key] = {
                "latitude": lat_grid,
                "longitude": lon_grid,
                "count": 0,
                "threats": 0
            }
        
        heatmap_data[key]["count"] += 1
        if det.is_threat:
            heatmap_data[key]["threats"] += 1
    
    return {
        "resolution": resolution,
        "period_days": days,
        "heatmap": list(heatmap_data.values())
    }


@router.get("/patterns")
async def get_detection_patterns(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Analyze detection patterns (time of day, day of week, etc.)"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    detections = db.query(Detection).filter(
        Detection.timestamp >= start_date
    ).all()
    
    # Analyze patterns
    hour_patterns = {}
    day_patterns = {}
    event_type_patterns = {}
    
    for det in detections:
        # Hour of day
        hour = det.timestamp.hour
        hour_patterns[hour] = hour_patterns.get(hour, 0) + 1
        
        # Day of week (0=Monday, 6=Sunday)
        day = det.timestamp.weekday()
        day_patterns[day] = day_patterns.get(day, 0) + 1
        
        # Event type
        event_type_patterns[det.event_type] = event_type_patterns.get(det.event_type, 0) + 1
    
    return {
        "period_days": days,
        "by_hour": hour_patterns,
        "by_day_of_week": day_patterns,
        "by_event_type": event_type_patterns,
        "peak_hour": max(hour_patterns.items(), key=lambda x: x[1])[0] if hour_patterns else None,
        "peak_day": max(day_patterns.items(), key=lambda x: x[1])[0] if day_patterns else None
    }


@router.get("/correlations")
async def get_correlations(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get correlations between different event types and locations"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    detections = db.query(Detection).filter(
        Detection.timestamp >= start_date
    ).all()
    
    # Analyze correlations
    event_location = {}
    event_time_correlation = {}
    
    for det in detections:
        # Event type and location correlation
        if det.latitude and det.longitude:
            location_key = f"{round(det.latitude, 2)},{round(det.longitude, 2)}"
            if location_key not in event_location:
                event_location[location_key] = {}
            event_location[location_key][det.event_type] = event_location[location_key].get(det.event_type, 0) + 1
        
        # Time-based correlations (hour)
        hour = det.timestamp.hour
        if hour not in event_time_correlation:
            event_time_correlation[hour] = {}
        event_time_correlation[hour][det.event_type] = event_time_correlation[hour].get(det.event_type, 0) + 1
    
    return {
        "period_days": days,
        "location_event_correlation": event_location,
        "time_event_correlation": event_time_correlation
    }


@router.get("/summary")
async def get_analytics_summary(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get comprehensive analytics summary"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total counts
    total = db.query(func.count(Detection.id)).filter(
        Detection.timestamp >= start_date
    ).scalar()
    
    threats = db.query(func.count(Detection.id)).filter(
        and_(
            Detection.timestamp >= start_date,
            Detection.is_threat == True
        )
    ).scalar()
    
    # Average confidence
    avg_confidence = db.query(func.avg(Detection.confidence)).filter(
        Detection.timestamp >= start_date
    ).scalar() or 0
    
    # Most common event type
    most_common = db.query(
        Detection.event_type,
        func.count(Detection.id).label('count')
    ).filter(
        Detection.timestamp >= start_date
    ).group_by(Detection.event_type).order_by(func.count(Detection.id).desc()).first()
    
    # Detection rate (per day)
    detection_rate = total / days if days > 0 else 0
    
    # Threat rate
    threat_rate = (threats / total * 100) if total > 0 else 0
    
    return {
        "period_days": days,
        "total_detections": total,
        "threat_detections": threats,
        "non_threat_detections": total - threats,
        "average_confidence": float(avg_confidence),
        "detection_rate_per_day": round(detection_rate, 2),
        "threat_percentage": round(threat_rate, 2),
        "most_common_event": {
            "type": most_common[0] if most_common else None,
            "count": most_common[1] if most_common else 0
        }
    }

