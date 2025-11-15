"""
Audio processing endpoints
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import os
from datetime import datetime
import aiofiles
from io import BytesIO

from backend.database import get_db
from backend.models import Detection, Hydrophone
from backend.ml.audio_processor import AudioProcessor
from backend.ml.model import EchoGuardModel
from backend.config import settings
from backend.services.alert_service import AlertService
from backend.utils.audio_utils import validate_audio_file, get_audio_info, convert_audio_format
from backend.utils.spectrogram import generate_spectrogram, generate_waveform
from backend.routers.websocket import manager

router = APIRouter()

# Initialize ML components
audio_processor = AudioProcessor(
    sample_rate=settings.SAMPLE_RATE,
    duration=settings.AUDIO_CHUNK_DURATION
)
ml_model = EchoGuardModel(model_path=settings.MODEL_PATH)
alert_service = AlertService()


@router.post("/analyze")
async def analyze_audio(
    file: UploadFile = File(...),
    hydrophone_id: Optional[int] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Analyze uploaded audio file for acoustic events
    """
    try:
        # Read audio file
        audio_bytes = await file.read()
        
        # Validate file type
        if not file.filename.lower().endswith(('.wav', '.mp3', '.flac', '.ogg')):
            raise HTTPException(status_code=400, detail="Unsupported audio format")
        
        # Save uploaded file
        upload_dir = "./uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{datetime.utcnow().timestamp()}_{file.filename}")
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(audio_bytes)
        
        # Process audio
        features = audio_processor.preprocess_audio(audio_bytes=audio_bytes)
        
        # Run ML prediction
        prediction = ml_model.predict(features)
        
        # Get hydrophone if provided
        hydrophone = None
        if hydrophone_id:
            hydrophone = db.query(Hydrophone).filter(Hydrophone.id == hydrophone_id).first()
            if not hydrophone:
                raise HTTPException(status_code=404, detail="Hydrophone not found")
        
        # Create detection record
        detection = Detection(
            hydrophone_id=hydrophone_id,
            event_type=prediction["event_type"],
            confidence=prediction["confidence"],
            audio_file_path=file_path,
            is_threat=prediction["is_threat"],
            latitude=latitude or (hydrophone.latitude if hydrophone else None),
            longitude=longitude or (hydrophone.longitude if hydrophone else None),
            metadata=prediction["class_probabilities"]
        )
        
        db.add(detection)
        db.commit()
        db.refresh(detection)
        
        # Send alert if threat detected
        if prediction["is_threat"] and settings.ENABLE_ALERTS:
            await alert_service.send_alert(detection, db)
        
        # Broadcast detection via WebSocket
        detection_data = {
            "detection_id": detection.id,
            "event_type": prediction["event_type"],
            "confidence": prediction["confidence"],
            "is_threat": prediction["is_threat"],
            "timestamp": detection.timestamp.isoformat(),
            "latitude": detection.latitude,
            "longitude": detection.longitude
        }
        await manager.broadcast_detection(detection_data)
        
        # Broadcast alert if threat
        if prediction["is_threat"]:
            await manager.broadcast_alert({
                "detection_id": detection.id,
                "event_type": prediction["event_type"],
                "confidence": prediction["confidence"],
                "message": f"Threat detected: {prediction['event_type']}"
            })
        
        return {
            "detection_id": detection.id,
            "event_type": prediction["event_type"],
            "confidence": prediction["confidence"],
            "is_threat": prediction["is_threat"],
            "class_probabilities": prediction["class_probabilities"],
            "timestamp": detection.timestamp.isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")


@router.post("/analyze/batch")
async def analyze_audio_batch(
    files: List[UploadFile] = File(...),
    hydrophone_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Analyze multiple audio files in batch"""
    results = []
    errors = []
    
    for file in files:
        try:
            # Validate file
            is_valid, error_msg = validate_audio_file(file.filename)
            if not is_valid:
                errors.append({"file": file.filename, "error": error_msg})
                continue
            
            # Read file
            audio_bytes = await file.read()
            
            # Process
            features = audio_processor.preprocess_audio(audio_bytes=audio_bytes)
            prediction = ml_model.predict(features)
            
            # Save file
            upload_dir = "./uploads"
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, f"{datetime.utcnow().timestamp()}_{file.filename}")
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(audio_bytes)
            
            # Create detection
            detection = Detection(
                hydrophone_id=hydrophone_id,
                event_type=prediction["event_type"],
                confidence=prediction["confidence"],
                audio_file_path=file_path,
                is_threat=prediction["is_threat"],
                metadata=prediction["class_probabilities"]
            )
            
            db.add(detection)
            db.commit()
            db.refresh(detection)
            
            results.append({
                "file": file.filename,
                "detection_id": detection.id,
                "event_type": prediction["event_type"],
                "confidence": prediction["confidence"],
                "is_threat": prediction["is_threat"]
            })
            
            # Send alert if threat
            if prediction["is_threat"] and settings.ENABLE_ALERTS:
                await alert_service.send_alert(detection, db)
        
        except Exception as e:
            errors.append({"file": file.filename, "error": str(e)})
    
    return {
        "processed": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors
    }


@router.get("/info/{detection_id}")
async def get_audio_info(detection_id: int, db: Session = Depends(get_db)):
    """Get audio file information for a detection"""
    detection = db.query(Detection).filter(Detection.id == detection_id).first()
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    if not detection.audio_file_path or not os.path.exists(detection.audio_file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    try:
        info = get_audio_info(detection.audio_file_path)
        return {
            "detection_id": detection_id,
            "audio_info": info,
            "detection": {
                "event_type": detection.event_type,
                "confidence": detection.confidence,
                "timestamp": detection.timestamp.isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading audio info: {str(e)}")


@router.get("/spectrogram/{detection_id}")
async def get_spectrogram(
    detection_id: int,
    db: Session = Depends(get_db),
    format: str = "png"
):
    """Generate spectrogram for a detection's audio file"""
    detection = db.query(Detection).filter(Detection.id == detection_id).first()
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    if not detection.audio_file_path or not os.path.exists(detection.audio_file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    try:
        spectrogram = generate_spectrogram(
            audio_path=detection.audio_file_path,
            sample_rate=settings.SAMPLE_RATE,
            format=format
        )
        return StreamingResponse(
            spectrogram,
            media_type=f"image/{format}",
            headers={"Content-Disposition": f"attachment; filename=spectrogram_{detection_id}.{format}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating spectrogram: {str(e)}")


@router.get("/waveform/{detection_id}")
async def get_waveform(
    detection_id: int,
    db: Session = Depends(get_db),
    format: str = "png"
):
    """Generate waveform visualization for a detection's audio file"""
    detection = db.query(Detection).filter(Detection.id == detection_id).first()
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    if not detection.audio_file_path or not os.path.exists(detection.audio_file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    try:
        waveform = generate_waveform(
            audio_path=detection.audio_file_path,
            sample_rate=settings.SAMPLE_RATE,
            format=format
        )
        return StreamingResponse(
            waveform,
            media_type=f"image/{format}",
            headers={"Content-Disposition": f"attachment; filename=waveform_{detection_id}.{format}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating waveform: {str(e)}")


@router.get("/download/{detection_id}")
async def download_audio(detection_id: int, db: Session = Depends(get_db)):
    """Download the original audio file for a detection"""
    detection = db.query(Detection).filter(Detection.id == detection_id).first()
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    if not detection.audio_file_path or not os.path.exists(detection.audio_file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        detection.audio_file_path,
        media_type="audio/wav",
        filename=f"detection_{detection_id}_{os.path.basename(detection.audio_file_path)}"
    )


@router.get("/health")
async def audio_service_health():
    """Check audio processing service health"""
    return {
        "status": "healthy",
        "model_loaded": ml_model.model is not None,
        "sample_rate": settings.SAMPLE_RATE,
        "chunk_duration": settings.AUDIO_CHUNK_DURATION
    }

