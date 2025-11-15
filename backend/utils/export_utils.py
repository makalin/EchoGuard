"""
Data export utilities
"""
import csv
import json
import pandas as pd
from typing import List, Dict, Any
from io import StringIO, BytesIO
from datetime import datetime
from sqlalchemy.orm import Session
from backend.models import Detection, Hydrophone


def export_detections_csv(detections: List[Detection], include_metadata: bool = False) -> str:
    """Export detections to CSV format"""
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    headers = [
        "id", "timestamp", "event_type", "confidence", "is_threat",
        "latitude", "longitude", "hydrophone_id", "hydrophone_name"
    ]
    if include_metadata:
        headers.append("metadata")
    
    writer.writerow(headers)
    
    # Data rows
    for det in detections:
        row = [
            det.id,
            det.timestamp.isoformat(),
            det.event_type,
            det.confidence,
            det.is_threat,
            det.latitude,
            det.longitude,
            det.hydrophone_id,
            det.hydrophone.name if det.hydrophone else None
        ]
        if include_metadata:
            row.append(json.dumps(det.metadata) if det.metadata else "")
        writer.writerow(row)
    
    return output.getvalue()


def export_detections_json(detections: List[Detection], include_metadata: bool = False) -> str:
    """Export detections to JSON format"""
    data = []
    for det in detections:
        item = {
            "id": det.id,
            "timestamp": det.timestamp.isoformat(),
            "event_type": det.event_type,
            "confidence": det.confidence,
            "is_threat": det.is_threat,
            "latitude": det.latitude,
            "longitude": det.longitude,
            "hydrophone_id": det.hydrophone_id,
            "hydrophone_name": det.hydrophone.name if det.hydrophone else None
        }
        if include_metadata:
            item["metadata"] = det.metadata
        data.append(item)
    
    return json.dumps(data, indent=2)


def export_detections_excel(detections: List[Detection], include_metadata: bool = False) -> BytesIO:
    """Export detections to Excel format"""
    data = []
    for det in detections:
        row = {
            "ID": det.id,
            "Timestamp": det.timestamp.isoformat(),
            "Event Type": det.event_type,
            "Confidence": det.confidence,
            "Is Threat": det.is_threat,
            "Latitude": det.latitude,
            "Longitude": det.longitude,
            "Hydrophone ID": det.hydrophone_id,
            "Hydrophone Name": det.hydrophone.name if det.hydrophone else None
        }
        if include_metadata and det.metadata:
            for key, value in det.metadata.items():
                row[f"Metadata_{key}"] = value
        data.append(row)
    
    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return output


def export_statistics_report(db: Session, days: int = 30) -> Dict[str, Any]:
    """Generate comprehensive statistics report"""
    from sqlalchemy import func, and_
    from datetime import datetime, timedelta
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total detections
    total = db.query(Detection).filter(Detection.timestamp >= start_date).count()
    
    # Threat detections
    threats = db.query(Detection).filter(
        and_(Detection.timestamp >= start_date, Detection.is_threat == True)
    ).count()
    
    # By event type
    event_types = db.query(
        Detection.event_type,
        func.count(Detection.id).label('count'),
        func.avg(Detection.confidence).label('avg_confidence')
    ).filter(
        Detection.timestamp >= start_date
    ).group_by(Detection.event_type).all()
    
    # By hydrophone
    hydrophone_stats = db.query(
        Hydrophone.name,
        func.count(Detection.id).label('count')
    ).join(
        Detection, Hydrophone.id == Detection.hydrophone_id
    ).filter(
        Detection.timestamp >= start_date
    ).group_by(Hydrophone.name).all()
    
    # Daily breakdown
    daily = db.query(
        func.date(Detection.timestamp).label('date'),
        func.count(Detection.id).label('count')
    ).filter(
        Detection.timestamp >= start_date
    ).group_by(func.date(Detection.timestamp)).order_by('date').all()
    
    return {
        "period": {
            "start": start_date.isoformat(),
            "end": datetime.utcnow().isoformat(),
            "days": days
        },
        "summary": {
            "total_detections": total,
            "threat_detections": threats,
            "non_threat_detections": total - threats,
            "threat_percentage": round((threats / total * 100) if total > 0 else 0, 2)
        },
        "by_event_type": [
            {
                "event_type": et,
                "count": count,
                "avg_confidence": float(avg_conf) if avg_conf else 0
            }
            for et, count, avg_conf in event_types
        ],
        "by_hydrophone": [
            {"name": name, "count": count}
            for name, count in hydrophone_stats
        ],
        "daily_breakdown": [
            {"date": str(date), "count": count}
            for date, count in daily
        ]
    }

