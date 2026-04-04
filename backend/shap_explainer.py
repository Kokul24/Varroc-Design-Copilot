"""
shap_explainer.py — Compute SHAP values for model explainability.
Uses TreeExplainer for tree-based models, with KernelExplainer as fallback.
"""

import numpy as np
import shap
from model_loader import get_model

# Feature names in the correct order
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
}

_explainer = None


def _get_explainer():
    """Create and cache the SHAP explainer."""
    global _explainer
    if _explainer is None:
        model = get_model()
        try:
            # Try TreeExplainer first (works for tree-based models like RF, GBM, XGBoost)
            _explainer = shap.TreeExplainer(model)
        except Exception:
            # Fallback to KernelExplainer for other model types
            # Create a small background dataset for KernelExplainer
            background = np.array([
                [2.0, 3.0, 1.0, 3.0, 0, 0.8, 1],
                [1.0, 1.0, 0.3, 8.0, 1, 0.4, 0],
                [5.0, 5.0, 2.5, 2.0, 0, 0.9, 2],
                [0.8, 0.5, 0.2, 12.0, 1, 0.3, 3],
                [3.0, 2.0, 1.5, 5.0, 0, 0.7, 1],
            ])
            predict_fn = (
                model.predict_proba
                if hasattr(model, "predict_proba")
                else model.predict
            )
            _explainer = shap.KernelExplainer(predict_fn, background)
    return _explainer


def compute_shap_values(features: dict) -> dict:
    """
    Compute SHAP values for a single prediction.

    Args:
        features: Dictionary of feature name → value

    Returns:
        Dictionary with:
            - shap_values: {feature_name: contribution_value}
            - base_value: model's expected output
            - feature_values: {feature_name: actual_value}
    """
    model = get_model()
    explainer = _get_explainer()

    # Build feature vector
    feature_vector = np.array([[features[f] for f in FEATURE_NAMES]])

    # Compute SHAP values
    shap_values = explainer.shap_values(feature_vector)

    # Handle multi-output (e.g., for classifiers with predict_proba)
    if isinstance(shap_values, list):
        # Use SHAP values for the positive class (class 1 = high risk)
        sv = shap_values[1][0] if len(shap_values) > 1 else shap_values[0][0]
    else:
        sv = shap_values[0]

    # Get base value
    if hasattr(explainer, "expected_value"):
        base_value = explainer.expected_value
        if isinstance(base_value, (list, np.ndarray)):
            base_value = float(base_value[1]) if len(base_value) > 1 else float(base_value[0])
        else:
            base_value = float(base_value)
    else:
        base_value = 0.5

    # Build result dictionary
    shap_dict = {}
    feature_val_dict = {}
    for i, fname in enumerate(FEATURE_NAMES):
        shap_dict[fname] = round(float(sv[i]), 4)
        feature_val_dict[fname] = features[fname]

    return {
        "shap_values": shap_dict,
        "base_value": round(base_value, 4),
        "feature_values": feature_val_dict,
        "feature_labels": FEATURE_LABELS,
    }
