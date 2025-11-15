"""
ML Model for acoustic event classification
"""
import numpy as np
import tensorflow as tf
from tensorflow import keras
from typing import Dict, Tuple, Optional
import os
import logging

logger = logging.getLogger(__name__)


class EchoGuardModel:
    """EchoGuard acoustic event classification model"""
    
    CLASSES = [
        "marine_life",      # 0 - Whale, dolphin, etc.
        "vessel",           # 1 - Boat/ship engine
        "blast_fishing",    # 2 - Underwater explosion
        "seismic",          # 3 - Seismic airgun
        "ambient"           # 4 - Background noise
    ]
    
    THREAT_CLASSES = ["vessel", "blast_fishing", "seismic"]
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or "./models/echoguard_model.h5"
        self.model = None
        self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Load existing model or create a new one"""
        if os.path.exists(self.model_path):
            try:
                self.model = keras.models.load_model(self.model_path)
                logger.info(f"Loaded model from {self.model_path}")
            except Exception as e:
                logger.warning(f"Could not load model: {e}. Creating new model.")
                self._create_model()
        else:
            logger.info("Model file not found. Creating new model.")
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            self._create_model()
    
    def _create_model(self):
        """Create a new CNN model architecture"""
        input_shape = (12000,)  # Feature vector size
        
        model = keras.Sequential([
            keras.layers.Reshape((120, 100), input_shape=input_shape),
            keras.layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Conv2D(128, (3, 3), activation='relu', padding='same'),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Flatten(),
            keras.layers.Dense(256, activation='relu'),
            keras.layers.Dropout(0.5),
            keras.layers.Dense(128, activation='relu'),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(len(self.CLASSES), activation='softmax')
        ])
        
        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        self.model = model
        # Save the untrained model structure
        self.model.save(self.model_path)
        logger.info(f"Created new model at {self.model_path}")
    
    def predict(self, features: np.ndarray) -> Dict[str, any]:
        """Predict acoustic event class from features"""
        if self.model is None:
            raise ValueError("Model not initialized")
        
        # Ensure features are in correct shape (flatten if needed)
        if len(features.shape) > 1:
            features = features.flatten()
        
        # Ensure correct length
        if len(features) != 12000:
            # Pad or trim to 12000
            if len(features) < 12000:
                padding = np.zeros(12000 - len(features))
                features = np.concatenate([features, padding])
            else:
                features = features[:12000]
        
        # Reshape for model input
        features = features.reshape(1, -1)
        
        predictions = self.model.predict(features, verbose=0)
        class_idx = np.argmax(predictions[0])
        confidence = float(predictions[0][class_idx])
        class_name = self.CLASSES[class_idx]
        
        # Get all class probabilities
        class_probs = {
            self.CLASSES[i]: float(predictions[0][i])
            for i in range(len(self.CLASSES))
        }
        
        return {
            "event_type": class_name,
            "confidence": confidence,
            "is_threat": class_name in self.THREAT_CLASSES,
            "class_probabilities": class_probs
        }
    
    def predict_batch(self, features_list: list) -> list:
        """Predict multiple audio samples"""
        results = []
        for features in features_list:
            results.append(self.predict(features))
        return results

