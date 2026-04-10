"""
shap_explainer.py — SHAP explainability module.

Now delegates to ml.inference for SHAP computation, maintaining
the same public interface for main.py and other modules.
"""

import os
import sys
import numpy as np

# Ensure ml package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ml.inference import _compute_shap_safe, _build_feature_vector, _load_model
from ml.inference import _feature_columns
from ml.utils import compute_continuous_penalties

# Feature names in the correct order (for backward compatibility)
FEATURE_NAMES = [
    "wall_thickness",
    "draft_angle",
    "corner_radius",
    "aspect_ratio",
    "undercut_present",
    "wall_uniformity",
    "material_encoded",
]

# Human-readable labels for features
FEATURE_LABELS = {
    "wall_thickness": "Wall Thickness",
    "draft_angle": "Draft Angle",
    "corner_radius": "Corner Radius",
    "aspect_ratio": "Aspect Ratio",
    "undercut_present": "Undercut Present",
    "wall_uniformity": "Wall Uniformity",
    "material_encoded": "Material Type",
    "wall_ar_interaction": "Wall-AR Interaction",
    "draft_undercut_interaction": "Draft-Undercut Interaction",
    "wall_uniformity_interaction": "Wall-Uniformity Interaction",
}


def compute_shap_values(features: dict) -> dict:
    """
    Compute SHAP values for a single prediction.

    Uses TreeExplainer for tree-based models with KernelExplainer fallback.
    If SHAP computation fails entirely, uses penalty-based explanation.

    Args:
        features: Dictionary of feature name → value

    Returns:
        Dictionary with:
            - shap_values: {feature_name: contribution_value}
            - base_value: model's expected output
            - feature_values: {feature_name: actual_value}
            - feature_labels: {feature_name: display_name}
    """
    try:
        # Try to use the ML inference pipeline's SHAP computation
        _load_model()
        feature_vector = _build_feature_vector(features)
        penalty_result = compute_continuous_penalties(features)

        result = _compute_shap_safe(feature_vector, features, penalty_result)
        return result

    except Exception as e:
        print(f"[shap_explainer] SHAP computation failed: {e}")
        # Fallback: return penalty-based pseudo-SHAP values
        penalty_result = compute_continuous_penalties(features)

        shap_dict = {
            "wall_thickness": penalty_result.get("penalty_wall", 0.0),
            "draft_angle": penalty_result.get("penalty_draft", 0.0),
            "corner_radius": penalty_result.get("penalty_corner", 0.0),
            "aspect_ratio": penalty_result.get("penalty_ar", 0.0),
            "undercut_present": penalty_result.get("penalty_undercut", 0.0),
            "wall_uniformity": penalty_result.get("penalty_uniformity", 0.0),
            "material_encoded": 0.0,
        }

        return {
            "shap_values": shap_dict,
            "base_value": 50.0,
            "feature_values": {k: features.get(k, 0) for k in FEATURE_NAMES},
            "feature_labels": FEATURE_LABELS,
        }
