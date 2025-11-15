"""
Audio utility functions
"""
import librosa
import numpy as np
import soundfile as sf
from typing import Tuple, Optional
import io
import os


def validate_audio_file(file_path: str) -> Tuple[bool, Optional[str]]:
    """Validate audio file format and integrity"""
    try:
        # Check file extension
        valid_extensions = ('.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac')
        if not file_path.lower().endswith(valid_extensions):
            return False, f"Unsupported file format. Supported: {valid_extensions}"
        
        # Check file exists
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        # Try to load audio
        try:
            y, sr = librosa.load(file_path, sr=None, duration=1.0)
            if len(y) == 0:
                return False, "Audio file appears to be empty"
            return True, None
        except Exception as e:
            return False, f"Invalid audio file: {str(e)}"
    
    except Exception as e:
        return False, f"Error validating file: {str(e)}"


def get_audio_info(file_path: str) -> dict:
    """Get audio file metadata"""
    try:
        y, sr = librosa.load(file_path, sr=None)
        duration = len(y) / sr
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        return {
            "sample_rate": int(sr),
            "duration": float(duration),
            "channels": 1 if len(y.shape) == 1 else y.shape[1],
            "file_size": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "format": os.path.splitext(file_path)[1].lower()
        }
    except Exception as e:
        raise ValueError(f"Error reading audio info: {str(e)}")


def convert_audio_format(
    input_path: str,
    output_path: str,
    target_format: str = 'wav',
    sample_rate: int = 22050
) -> str:
    """Convert audio file to target format"""
    try:
        y, sr = librosa.load(input_path, sr=sample_rate)
        sf.write(output_path, y, sample_rate, format=target_format)
        return output_path
    except Exception as e:
        raise ValueError(f"Error converting audio: {str(e)}")


def extract_audio_segment(
    file_path: str,
    start_time: float,
    end_time: float,
    output_path: Optional[str] = None
) -> np.ndarray:
    """Extract a segment from audio file"""
    try:
        y, sr = librosa.load(
            file_path,
            offset=start_time,
            duration=end_time - start_time
        )
        if output_path:
            sf.write(output_path, y, sr)
        return y
    except Exception as e:
        raise ValueError(f"Error extracting segment: {str(e)}")

