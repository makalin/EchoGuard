"""
Alert service for threat notifications
"""
import httpx
import logging
from typing import Optional
from sqlalchemy.orm import Session

from backend.models import Alert, Detection
from backend.config import settings

logger = logging.getLogger(__name__)


class AlertService:
    """Service for sending alerts when threats are detected"""
    
    async def send_alert(self, detection: Detection, db: Session):
        """Send alert for threat detection"""
        try:
            # Create alert record
            alert = Alert(
                detection_id=detection.id,
                alert_type="webhook",
                status="pending",
                message=f"Threat detected: {detection.event_type} (confidence: {detection.confidence:.2f})"
            )
            db.add(alert)
            db.commit()
            
            # Send webhook if configured
            if settings.ALERT_WEBHOOK_URL:
                await self._send_webhook(detection, alert)
            
            # Update alert status
            alert.status = "sent"
            db.commit()
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            if 'alert' in locals():
                alert.status = "failed"
                db.commit()
    
    async def _send_webhook(self, detection: Detection, alert: Alert):
        """Send webhook notification"""
        if not settings.ALERT_WEBHOOK_URL:
            return
        
        payload = {
            "detection_id": detection.id,
            "event_type": detection.event_type,
            "confidence": detection.confidence,
            "timestamp": detection.timestamp.isoformat(),
            "latitude": detection.latitude,
            "longitude": detection.longitude,
            "message": alert.message
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    settings.ALERT_WEBHOOK_URL,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
            except Exception as e:
                logger.error(f"Webhook failed: {e}")
                raise

