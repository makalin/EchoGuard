"""
Audio processing utilities for feature extraction
"""
import numpy as np
import librosa
import soundfile as sf
from typing import Tuple, Optional
import io


class AudioProcessor:
    """Process audio files for ML model input"""
    
    def __init__(self, sample_rate: int = 22050, duration: float = 5.0):
        self.sample_rate = sample_rate
        self.duration = duration
        self.target_length = int(sample_rate * duration)
    
    def load_audio(self, audio_path: str) -> Tuple[np.ndarray, int]:
        """Load audio file and resample if needed"""
        try:
            y, sr = librosa.load(audio_path, sr=self.sample_rate, duration=self.duration)
            return y, sr
        except Exception as e:
            raise ValueError(f"Error loading audio: {str(e)}")
    
    def load_audio_from_bytes(self, audio_bytes: bytes) -> Tuple[np.ndarray, int]:
        """Load audio from bytes (e.g., uploaded file)"""
        try:
            audio_io = io.BytesIO(audio_bytes)
            y, sr = librosa.load(audio_io, sr=self.sample_rate, duration=self.duration)
            return y, sr
        except Exception as e:
            raise ValueError(f"Error loading audio from bytes: {str(e)}")
    
    def extract_features(self, audio: np.ndarray) -> np.ndarray:
        """Extract features for ML model"""
        features = []
        
        # Mel Spectrogram
        mel_spec = librosa.feature.melspectrogram(
            y=audio, 
            sr=self.sample_rate, 
            n_mels=128,
            hop_length=512
        )
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        features.append(mel_spec_db.flatten()[:128 * 87])  # Flatten and pad/trim
        
        # MFCCs
        mfccs = librosa.feature.mfcc(y=audio, sr=self.sample_rate, n_mfcc=13)
        features.append(mfccs.flatten()[:13 * 87])
        
        # Spectral features
        spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=self.sample_rate)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=audio, sr=self.sample_rate)[0]
        zero_crossing_rate = librosa.feature.zero_crossing_rate(audio)[0]
        
        features.append(spectral_centroids[:87])
        features.append(spectral_rolloff[:87])
        features.append(zero_crossing_rate[:87])
        
        # Combine all features
        feature_vector = np.concatenate(features)
        
        # Pad or trim to fixed size
        target_size = 128 * 87 + 13 * 87 + 87 * 3  # ~12,000 features
        if len(feature_vector) < target_size:
            feature_vector = np.pad(feature_vector, (0, target_size - len(feature_vector)))
        else:
            feature_vector = feature_vector[:target_size]
        
        return feature_vector.reshape(1, -1)
    
    def preprocess_audio(self, audio_path: Optional[str] = None, audio_bytes: Optional[bytes] = None) -> np.ndarray:
        """Complete preprocessing pipeline"""
        if audio_path:
            audio, _ = self.load_audio(audio_path)
        elif audio_bytes:
            audio, _ = self.load_audio_from_bytes(audio_bytes)
        else:
            raise ValueError("Either audio_path or audio_bytes must be provided")
        
        # Pad or trim to target length
        if len(audio) < self.target_length:
            audio = np.pad(audio, (0, self.target_length - len(audio)))
        else:
            audio = audio[:self.target_length]
        
        return self.extract_features(audio)

