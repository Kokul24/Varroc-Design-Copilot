"""
ml/inference.py — Inference module for DFM risk prediction.

Handles:
- Loading and caching the trained model
- Preprocessing inputs identically to training
- Computing predictions with both ML model and penalty-based scoring
- SHAP-based explainability
- Top failure reason ranking
- Confidence score generation

All edge cases are handled gracefully.
"""

import os
import math
import warnings
import numpy as np
import joblib

warnings.filterwarnings("ignore")

from ml.utils import (
    validate_input_features,
    encode_material,
    compute_continuous_penalties,
    compute_interaction_penalty,
    compute_confidence,
    get_risk_label,
    stable_sigmoid,
    clamp_features,
    THRESHOLDS,
    PENALTY_WEIGHTS,
)

# ============================================================
# Paths
# ============================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
FEATURE_COLS_PATH = os.path.join(BASE_DIR, "feature_columns.pkl")
LABEL_ENCODER_PATH = os.path.join(BASE_DIR, "label_encoder.pkl")

# ============================================================
# Cached model state (loaded once, reused)
# ============================================================
_model = None
_feature_columns = None
_label_encoder = None
_shap_explainer = None


def _load_model():
    """Load and cache the trained model and associated artifacts."""
    global _model, _feature_columns, _label_encoder

    if _model is not None:
        return

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Model file not found at {MODEL_PATH}. "
            "Run 'python -m ml.train' from the backend directory to train the model."
        )

    _model = joblib.load(MODEL_PATH)
    print(f"[inference] Model loaded from {MODEL_PATH}")

    if os.path.exists(FEATURE_COLS_PATH):
        _feature_columns = joblib.load(FEATURE_COLS_PATH)
        print(f"[inference] Feature columns: {_feature_columns}")
    else:
        # Default feature order (must match training)
        _feature_columns = [
            "wall_thickness", "draft_angle", "corner_radius",
            "aspect_ratio", "undercut_present", "wall_uniformity",
            "material_encoded",
            "wall_ar_interaction", "draft_undercut_interaction",
            "wall_uniformity_interaction",
        ]
        print("[inference] Using default feature columns")

    if os.path.exists(LABEL_ENCODER_PATH):
        _label_encoder = joblib.load(LABEL_ENCODER_PATH)
        print(f"[inference] Label encoder loaded with classes: {list(_label_encoder.classes_)}")
    else:
        _label_encoder = None
        print("[inference] No label encoder found, using default material encoding")


def get_model():
    """Get the cached model, loading it if necessary."""
    _load_model()
    return _model


def _get_shap_explainer():
    """Create and cache the SHAP explainer."""
    global _shap_explainer

    if _shap_explainer is not None:
        return _shap_explainer

    try:
        import shap
        model = get_model()

        try:
            # TreeExplainer for tree-based models (XGBoost, GBM, RF)
            _shap_explainer = shap.TreeExplainer(model)
            print("[inference] SHAP TreeExplainer initialized")
        except Exception:
            # Fallback to KernelExplainer
            background = np.array([
                [2.0, 1.5, 1.0, 4.0, 0, 0.7, 2, 0.0, 0.0, 0.0],
                [1.0, 0.5, 0.3, 10.0, 1, 0.4, 0, 0.25, 0.33, 0.17],
                [4.0, 3.0, 2.0, 3.0, 0, 0.9, 1, 0.0, 0.0, 0.0],
                [0.8, 0.2, 0.2, 12.0, 1, 0.3, 3, 0.2, 0.87, 0.4],
                [3.0, 2.0, 1.5, 5.0, 0, 0.8, 4, 0.0, 0.0, 0.0],
            ])
            # Trim background to match feature count
            n_features = len(_feature_columns) if _feature_columns else 10
            background = background[:, :n_features]

            predict_fn = model.predict
            _shap_explainer = shap.KernelExplainer(predict_fn, background)
            print("[inference] SHAP KernelExplainer initialized (fallback)")

    except Exception as e:
        print(f"[inference] Warning: Could not initialize SHAP explainer: {e}")
        _shap_explainer = None

    return _shap_explainer


def _build_feature_vector(features: dict) -> np.ndarray:
    """
    Build the feature vector in the correct order for the model.
    Includes engineered interaction features to match training.

    Args:
        features: Validated feature dictionary

    Returns:
        numpy array of shape (1, n_features)
    """
    _load_model()

    # Compute interaction features (same logic as training)
    min_wall = 1.0
    max_ar = 8.0
    min_draft = 1.5
    min_uniform = 0.6

    wall = features.get("wall_thickness", 0.0)
    draft = features.get("draft_angle", 0.0)
    ar = features.get("aspect_ratio", 1.0)
    undercut = features.get("undercut_present", 0)
    uniformity = features.get("wall_uniformity", 1.0)

    wall_deficit = max(0.0, min(1.0, (min_wall - wall) / min_wall))
    ar_excess = max(0.0, min(1.0, (ar - max_ar) / max_ar))
    draft_deficit = max(0.0, min(1.0, (min_draft - draft) / min_draft))
    uniform_deficit = max(0.0, min(1.0, (min_uniform - uniformity) / min_uniform))

    # Add interaction features to the features dict
    enriched = features.copy()
    enriched["wall_ar_interaction"] = wall_deficit * ar_excess
    enriched["draft_undercut_interaction"] = draft_deficit * undercut
    enriched["wall_uniformity_interaction"] = wall_deficit * uniform_deficit

    # Build vector in correct column order
    vector = []
    for col in _feature_columns:
        if col in enriched:
            vector.append(float(enriched[col]))
        else:
            vector.append(0.0)

    return np.array([vector])


def predict(features: dict) -> dict:
    """
    Make a full prediction with ML model + continuous scoring.

    This is the main inference entry point. It:
    1. Validates inputs
    2. Runs ML model prediction
    3. Computes continuous penalty-based scores
    4. Blends both signals
    5. Computes SHAP explanations
    6. Ranks top failure reasons
    7. Computes confidence score

    Args:
        features: Dictionary with manufacturing features.
                  Required: wall_thickness, draft_angle, corner_radius,
                           aspect_ratio, undercut_present, wall_uniformity
                  Optional: material (string) or material_encoded (int)

    Returns:
        Full prediction dictionary matching the API output format
    """
    try:
        _load_model()
    except FileNotFoundError as e:
        # Graceful degradation: use penalty-based scoring only
        return _penalty_only_predict(features)

    # --- 1. Validate and preprocess ---
    validated = validate_input_features(features)

    # Handle material encoding
    if "material_encoded" not in validated:
        material = validated.pop("material", "abs")
        if _label_encoder is not None and hasattr(_label_encoder, "classes_"):
            # Use the same encoder as training
            material_str = str(material).strip()
            if material_str in _label_encoder.classes_:
                validated["material_encoded"] = int(
                    _label_encoder.transform([material_str])[0]
                )
            else:
                # Try case-insensitive match
                for cls in _label_encoder.classes_:
                    if cls.lower() == material_str.lower():
                        validated["material_encoded"] = int(
                            _label_encoder.transform([cls])[0]
                        )
                        break
                else:
                    validated["material_encoded"] = encode_material(material_str)
        else:
            validated["material_encoded"] = encode_material(str(material))
    else:
        material = validated.get("material", "unknown")

    # --- 2. ML Model prediction ---
    feature_vector = _build_feature_vector(validated)

    model = get_model()
    is_regressor = hasattr(model, "predict") and not hasattr(model, "predict_proba")

    if is_regressor or (hasattr(model, "_estimator_type") and model._estimator_type == "regressor"):
        # Regression model: predicts risk_score directly (0-100)
        ml_risk_score = float(model.predict(feature_vector)[0])
        ml_risk_score = max(0.0, min(100.0, ml_risk_score))
        ml_probability = ml_risk_score / 100.0
    else:
        # Classification model: predicts probability
        if hasattr(model, "predict_proba"):
            probas = model.predict_proba(feature_vector)[0]
            ml_probability = float(probas[1]) if len(probas) > 1 else float(probas[0])
        else:
            ml_probability = float(model.predict(feature_vector)[0])
        ml_risk_score = round(ml_probability * 100.0, 2)

    # --- 3. Continuous penalty scoring ---
    penalty_result = compute_continuous_penalties(validated)
    penalty_risk_score = penalty_result["risk_score"]

    # --- 4. Blend ML + penalty scores ---
    # ML model gets higher weight since it's trained on real data
    # Penalty scoring provides physics-based sanity checking
    blended_score = round(0.7 * ml_risk_score + 0.3 * penalty_risk_score, 2)
    blended_score = max(0.0, min(100.0, blended_score))

    risk_label = get_risk_label(blended_score)

    # --- 5. Compute SHAP values ---
    shap_result = _compute_shap_safe(feature_vector, validated, penalty_result)

    # --- 6. Top failure reasons ---
    top_issues = _rank_failure_reasons(shap_result, penalty_result, validated)

    # --- 7. Confidence score ---
    confidence = compute_confidence(
        model_probability=ml_probability,
        penalty_magnitude=penalty_result["total_penalty"],
    )

    return {
        "risk_score": blended_score,
        "risk_label": risk_label,
        "probability": round(ml_probability, 4),
        "confidence": confidence,
        "top_issues": top_issues,
        "shap_values": shap_result.get("shap_values", {}),
        "shap_base_value": shap_result.get("base_value", 0.0),
        "features": validated,
        "penalty_breakdown": penalty_result,
        "ml_risk_score": round(ml_risk_score, 2),
        "penalty_risk_score": round(penalty_risk_score, 2),
    }


def _penalty_only_predict(features: dict) -> dict:
    """
    Fallback prediction using only penalty-based scoring.
    Used when the ML model is not available.
    """
    try:
        validated = validate_input_features(features)
    except ValueError:
        validated = clamp_features(features)

    if "material_encoded" not in validated:
        material = validated.pop("material", "abs")
        validated["material_encoded"] = encode_material(str(material))

    penalty_result = compute_continuous_penalties(validated)
    risk_score = penalty_result["risk_score"]
    risk_label = get_risk_label(risk_score)

    # Derive top issues from penalties
    top_issues = _rank_failure_reasons(
        {"shap_values": {}}, penalty_result, validated
    )

    confidence = compute_confidence(penalty_magnitude=penalty_result["total_penalty"])

    return {
        "risk_score": risk_score,
        "risk_label": risk_label,
        "probability": risk_score / 100.0,
        "confidence": confidence,
        "top_issues": top_issues,
        "shap_values": {},
        "shap_base_value": 0.0,
        "features": validated,
        "penalty_breakdown": penalty_result,
        "ml_risk_score": None,
        "penalty_risk_score": risk_score,
    }


def _compute_shap_safe(
    feature_vector: np.ndarray,
    features: dict,
    penalty_result: dict,
) -> dict:
    """
    Compute SHAP values with graceful fallback.

    If SHAP computation fails, falls back to penalty-based explanation.
    """
    _load_model()

    # Human-readable feature labels
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

    try:
        explainer = _get_shap_explainer()
        if explainer is None:
            raise RuntimeError("SHAP explainer not available")

        shap_values = explainer.shap_values(feature_vector)

        # Handle multi-output (classifiers)
        if isinstance(shap_values, list):
            sv = shap_values[1][0] if len(shap_values) > 1 else shap_values[0][0]
        elif len(shap_values.shape) == 3:
            # Shape: (n_samples, n_features, n_classes)
            sv = shap_values[0, :, 1] if shap_values.shape[2] > 1 else shap_values[0, :, 0]
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

        # Build SHAP dictionary — replace any NaN with 0
        shap_dict = {}
        for i, fname in enumerate(_feature_columns):
            val = float(sv[i]) if i < len(sv) else 0.0
            if math.isnan(val) or math.isinf(val):
                val = 0.0
            shap_dict[fname] = round(val, 4)

        return {
            "shap_values": shap_dict,
            "base_value": round(base_value, 4),
            "feature_values": {k: features.get(k, 0) for k in _feature_columns},
            "feature_labels": FEATURE_LABELS,
        }

    except Exception as e:
        print(f"[inference] SHAP computation failed, using penalty fallback: {e}")
        return _penalty_based_explanation(penalty_result, features, FEATURE_LABELS)


def _penalty_based_explanation(
    penalty_result: dict,
    features: dict,
    feature_labels: dict,
) -> dict:
    """
    Generate explanation from penalty contributions when SHAP fails.
    Maps penalty components back to pseudo-SHAP values for consistent API.
    """
    shap_dict = {
        "wall_thickness": penalty_result.get("penalty_wall", 0.0),
        "draft_angle": penalty_result.get("penalty_draft", 0.0),
        "corner_radius": penalty_result.get("penalty_corner", 0.0),
        "aspect_ratio": penalty_result.get("penalty_ar", 0.0),
        "undercut_present": penalty_result.get("penalty_undercut", 0.0),
        "wall_uniformity": penalty_result.get("penalty_uniformity", 0.0),
        "material_encoded": 0.0,
        "wall_ar_interaction": penalty_result.get("interaction_penalty", 0.0) * 0.5,
        "draft_undercut_interaction": penalty_result.get("interaction_penalty", 0.0) * 0.3,
        "wall_uniformity_interaction": penalty_result.get("interaction_penalty", 0.0) * 0.2,
    }

    return {
        "shap_values": shap_dict,
        "base_value": 50.0,
        "feature_values": {k: features.get(k, 0) for k in shap_dict},
        "feature_labels": feature_labels,
    }


def _rank_failure_reasons(
    shap_result: dict,
    penalty_result: dict,
    features: dict,
) -> list:
    """
    Derive top 3 contributing failure factors.

    Uses SHAP values when available, falls back to penalty contributions.
    Returns formatted strings with percentage contributions.
    """
    FEATURE_DISPLAY_NAMES = {
        "wall_thickness": "Wall thickness",
        "draft_angle": "Draft angle",
        "corner_radius": "Corner radius",
        "aspect_ratio": "Aspect ratio",
        "undercut_present": "Undercut geometry",
        "wall_uniformity": "Wall uniformity",
        "material_encoded": "Material type",
        "wall_ar_interaction": "Wall-AR interaction",
        "draft_undercut_interaction": "Draft-undercut interaction",
        "wall_uniformity_interaction": "Wall-uniformity interaction",
    }

    contributions = {}

    # Try SHAP values first
    shap_vals = shap_result.get("shap_values", {})
    if shap_vals and any(abs(v) > 0.001 for v in shap_vals.values()):
        for feature, value in shap_vals.items():
            contributions[feature] = abs(value)
    else:
        # Fallback to penalty contributions
        penalty_map = {
            "wall_thickness": penalty_result.get("penalty_wall", 0),
            "draft_angle": penalty_result.get("penalty_draft", 0),
            "corner_radius": penalty_result.get("penalty_corner", 0),
            "aspect_ratio": penalty_result.get("penalty_ar", 0),
            "undercut_present": penalty_result.get("penalty_undercut", 0),
            "wall_uniformity": penalty_result.get("penalty_uniformity", 0),
        }
        contributions = {k: abs(v) for k, v in penalty_map.items()}

    # Sort by absolute contribution
    sorted_contributions = sorted(
        contributions.items(), key=lambda x: x[1], reverse=True
    )

    # Compute percentages from top contributors
    total = sum(v for _, v in sorted_contributions[:5])
    if total < 1e-8:
        return ["No significant risk factors identified"]

    top_issues = []
    for feature, value in sorted_contributions[:3]:
        pct = round((value / total) * 100)
        display_name = FEATURE_DISPLAY_NAMES.get(feature, feature)
        top_issues.append(f"{display_name} ({pct}%)")

    return top_issues
