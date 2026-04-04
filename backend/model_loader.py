"""
model_loader.py — Load pre-trained model and make predictions.
Handles loading model.pkl and computing risk scores + probabilities.
"""

import os
import joblib
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")

_model = None


def get_model():
    """Load and cache the pre-trained model."""
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Model file not found at {MODEL_PATH}. "
                "Run 'python create_mock_model.py' to generate a demo model."
            )
        _model = joblib.load(MODEL_PATH)
    return _model


def predict(features: dict) -> dict:
    """
    Make a prediction using the pre-trained model.

    Args:
        features: Dictionary with keys:
            wall_thickness, draft_angle, corner_radius, aspect_ratio,
            undercut_present, wall_uniformity, material_encoded

    Returns:
        Dictionary with risk_score, probability, and risk_label.
    """
    model = get_model()

    # Build feature vector in the correct order
    feature_order = [
        "wall_thickness",
        "draft_angle",
        "corner_radius",
        "aspect_ratio",
        "undercut_present",
        "wall_uniformity",
        "material_encoded",
    ]
    feature_vector = np.array([[features[f] for f in feature_order]])

    # Predict probability of high-risk
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(feature_vector)[0]
        # probability of being high-risk (class 1)
        risk_probability = float(probabilities[1]) if len(probabilities) > 1 else float(probabilities[0])
    else:
        risk_probability = float(model.predict(feature_vector)[0])

    # Convert probability to risk score (0–100)
    risk_score = round(risk_probability * 100, 1)

    # Determine risk label
    if risk_score < 40:
        risk_label = "LOW"
    elif risk_score <= 70:
        risk_label = "MEDIUM"
    else:
        risk_label = "HIGH"

    return {
        "risk_score": risk_score,
        "probability": round(risk_probability, 4),
        "risk_label": risk_label,
    }
