"""
Create and save a basic ML model structure
This is a placeholder - in production, you would train this with real data
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.ml.model import EchoGuardModel

# Create model directory
os.makedirs("./models", exist_ok=True)

# Initialize model (will create if doesn't exist)
model = EchoGuardModel(model_path="./models/echoguard_model.h5")

print("Model created/loaded successfully!")
print(f"Model path: {model.model_path}")
print(f"Classes: {model.CLASSES}")

