"""
Data export endpoints
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from io import BytesIO

from backend.database import get_db
from backend.models import Detection
from backend.utils.export_utils import (
    export_detections_csv,
    export_detections_json,
    export_detections_excel,
    export_statistics_report
)

router = APIRouter()


@router.get("/detections/csv")
async def export_detections_csv_endpoint(
    days: int = Query(30, ge=1, le=365),
    event_type: Optional[str] = None,
    is_threat: Optional[bool] = None,
    include_metadata: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Export detections to CSV"""
    from sqlalchemy import and_
    
    start_date = datetime.utcnow() - timedelta(days=days)
    query = db.query(Detection).filter(Detection.timestamp >= start_date)
    
    if event_type:
        query = query.filter(Detection.event_type == event_type)
    if is_threat is not None:
        query = query.filter(Detection.is_threat == is_threat)
    
    detections = query.all()
    
    csv_content = export_detections_csv(detections, include_metadata)
    
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=detections_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        }
    )


@router.get("/detections/json")
async def export_detections_json_endpoint(
    days: int = Query(30, ge=1, le=365),
    event_type: Optional[str] = None,
    is_threat: Optional[bool] = None,
    include_metadata: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Export detections to JSON"""
    from sqlalchemy import and_
    
    start_date = datetime.utcnow() - timedelta(days=days)
    query = db.query(Detection).filter(Detection.timestamp >= start_date)
    
    if event_type:
        query = query.filter(Detection.event_type == event_type)
    if is_threat is not None:
        query = query.filter(Detection.is_threat == is_threat)
    
    detections = query.all()
    
    json_content = export_detections_json(detections, include_metadata)
    
    return StreamingResponse(
        iter([json_content]),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=detections_{datetime.utcnow().strftime('%Y%m%d')}.json"
        }
    )


@router.get("/detections/excel")
async def export_detections_excel_endpoint(
    days: int = Query(30, ge=1, le=365),
    event_type: Optional[str] = None,
    is_threat: Optional[bool] = None,
    include_metadata: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Export detections to Excel"""
    from sqlalchemy import and_
    
    start_date = datetime.utcnow() - timedelta(days=days)
    query = db.query(Detection).filter(Detection.timestamp >= start_date)
    
    if event_type:
        query = query.filter(Detection.event_type == event_type)
    if is_threat is not None:
        query = query.filter(Detection.is_threat == is_threat)
    
    detections = query.all()
    
    excel_file = export_detections_excel(detections, include_metadata)
    
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=detections_{datetime.utcnow().strftime('%Y%m%d')}.xlsx"
        }
    )


@router.get("/statistics/report")
async def export_statistics_report_endpoint(
    days: int = Query(30, ge=1, le=365),
    format: str = Query("json", regex="^(json|csv)$"),
    db: Session = Depends(get_db)
):
    """Export comprehensive statistics report"""
    report = export_statistics_report(db, days)
    
    if format == "json":
        import json
        content = json.dumps(report, indent=2)
        return StreamingResponse(
            iter([content]),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=statistics_report_{datetime.utcnow().strftime('%Y%m%d')}.json"
            }
        )
    else:  # CSV
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write summary
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Detections", report["summary"]["total_detections"]])
        writer.writerow(["Threat Detections", report["summary"]["threat_detections"]])
        writer.writerow(["Non-Threat Detections", report["summary"]["non_threat_detections"]])
        writer.writerow(["Threat Percentage", report["summary"]["threat_percentage"]])
        writer.writerow([])
        
        # Write event types
        writer.writerow(["Event Type", "Count", "Avg Confidence"])
        for item in report["by_event_type"]:
            writer.writerow([item["event_type"], item["count"], item["avg_confidence"]])
        writer.writerow([])
        
        # Write hydrophones
        writer.writerow(["Hydrophone", "Count"])
        for item in report["by_hydrophone"]:
            writer.writerow([item["name"], item["count"]])
        
        content = output.getvalue()
        return StreamingResponse(
            iter([content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=statistics_report_{datetime.utcnow().strftime('%Y%m%d')}.csv"
            }
        )

