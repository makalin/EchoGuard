"""
Database models for EchoGuard
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from datetime import datetime
from backend.database import Base


class Hydrophone(Base):
    """Hydrophone sensor information"""
    __tablename__ = "hydrophones"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    location = Column(Geometry('POINT', srid=4326), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    depth = Column(Float, nullable=True)  # meters
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    detections = relationship("Detection", back_populates="hydrophone")


class Detection(Base):
    """Acoustic event detection record"""
    __tablename__ = "detections"
    
    id = Column(Integer, primary_key=True, index=True)
    hydrophone_id = Column(Integer, ForeignKey("hydrophones.id"), nullable=True)
    event_type = Column(String(100), nullable=False, index=True)  # blast_fishing, vessel, seismic, marine_life
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    audio_file_path = Column(String(500), nullable=True)
    duration = Column(Float, nullable=True)  # seconds
    frequency_range = Column(JSONB, nullable=True)  # {"min": 20, "max": 20000}
    metadata = Column(JSONB, nullable=True)  # Additional detection metadata
    is_threat = Column(Boolean, default=False, index=True)
    location = Column(Geometry('POINT', srid=4326), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    processed = Column(Boolean, default=False)
    
    hydrophone = relationship("Hydrophone", back_populates="detections")


class Alert(Base):
    """Alert records for threat detections"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    detection_id = Column(Integer, ForeignKey("detections.id"), nullable=False)
    alert_type = Column(String(100), nullable=False)  # email, webhook, sms
    status = Column(String(50), default="pending")  # pending, sent, failed
    sent_at = Column(DateTime, nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    detection = relationship("Detection")

