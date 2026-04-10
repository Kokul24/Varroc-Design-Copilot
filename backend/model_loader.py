"""
model_loader.py — Bridge module: connects existing API to the new ML inference pipeline.

This module maintains the same public interface (predict, get_model) that main.py
and other modules use, but delegates to the production ML pipeline in ml/inference.py.
"""

import os
import sys

# Add the backend directory to path so ml package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ml.inference import predict as ml_predict, get_model as ml_get_model


def get_model():
    """
    Load and cache the pre-trained model.
    Delegates to ml.inference for consistent model management.
    """
    return ml_get_model()


def predict(features: dict) -> dict:
    """
    Make a prediction using the trained ML pipeline.

    This wraps ml.inference.predict() and adapts the output to
    match the format expected by main.py and the rest of the backend.

    Args:
        features: Dictionary with keys:
            wall_thickness, draft_angle, corner_radius, aspect_ratio,
            undercut_present, wall_uniformity, material_encoded

    Returns:
        Dictionary with risk_score, probability, risk_label,
        confidence, top_issues, shap_values, etc.
    """
    # The new pipeline returns a comprehensive result dict
    result = ml_predict(features)

    # Return full result — main.py can use any fields it needs
    # Also ensure backward compatibility with the original interface
    return {
        # Original fields expected by main.py
        "risk_score": result["risk_score"],
        "probability": result["probability"],
        "risk_label": result["risk_label"],
        # New fields from the production pipeline
        "confidence": result["confidence"],
        "top_issues": result["top_issues"],
        "shap_values": result["shap_values"],
        "shap_base_value": result.get("shap_base_value", 0.0),
        "penalty_breakdown": result.get("penalty_breakdown", {}),
        "ml_risk_score": result.get("ml_risk_score"),
        "penalty_risk_score": result.get("penalty_risk_score"),
        "features": result.get("features", features),
    }
