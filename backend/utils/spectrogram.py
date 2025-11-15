"""
Spectrogram visualization utilities
"""
import librosa
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from io import BytesIO
from typing import Optional, Tuple


def generate_spectrogram(
    audio_path: Optional[str] = None,
    audio_data: Optional[np.ndarray] = None,
    sample_rate: int = 22050,
    n_fft: int = 2048,
    hop_length: int = 512,
    n_mels: int = 128,
    format: str = 'png',
    dpi: int = 100
) -> BytesIO:
    """Generate spectrogram image from audio"""
    try:
        # Load audio if path provided
        if audio_path:
            y, sr = librosa.load(audio_path, sr=sample_rate)
        elif audio_data is not None:
            y = audio_data
            sr = sample_rate
        else:
            raise ValueError("Either audio_path or audio_data must be provided")
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Generate mel spectrogram
        mel_spec = librosa.feature.melspectrogram(
            y=y,
            sr=sr,
            n_fft=n_fft,
            hop_length=hop_length,
            n_mels=n_mels
        )
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        
        # Plot
        img = librosa.display.specshow(
            mel_spec_db,
            x_axis='time',
            y_axis='mel',
            sr=sr,
            hop_length=hop_length,
            ax=ax,
            cmap='viridis'
        )
        
        ax.set_title('Mel Spectrogram', fontsize=14, fontweight='bold')
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Frequency (Hz)')
        fig.colorbar(img, ax=ax, format='%+2.0f dB')
        
        # Save to bytes
        buffer = BytesIO()
        fig.savefig(buffer, format=format, dpi=dpi, bbox_inches='tight')
        buffer.seek(0)
        plt.close(fig)
        
        return buffer
    
    except Exception as e:
        raise ValueError(f"Error generating spectrogram: {str(e)}")


def generate_waveform(
    audio_path: Optional[str] = None,
    audio_data: Optional[np.ndarray] = None,
    sample_rate: int = 22050,
    format: str = 'png',
    dpi: int = 100
) -> BytesIO:
    """Generate waveform visualization"""
    try:
        # Load audio if path provided
        if audio_path:
            y, sr = librosa.load(audio_path, sr=sample_rate)
        elif audio_data is not None:
            y = audio_data
            sr = sample_rate
        else:
            raise ValueError("Either audio_path or audio_data must be provided")
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 4))
        
        # Generate time axis
        time = np.linspace(0, len(y) / sr, len(y))
        
        # Plot waveform
        ax.plot(time, y, linewidth=0.5)
        ax.set_title('Audio Waveform', fontsize=14, fontweight='bold')
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Amplitude')
        ax.grid(True, alpha=0.3)
        
        # Save to bytes
        buffer = BytesIO()
        fig.savefig(buffer, format=format, dpi=dpi, bbox_inches='tight')
        buffer.seek(0)
        plt.close(fig)
        
        return buffer
    
    except Exception as e:
        raise ValueError(f"Error generating waveform: {str(e)}")

