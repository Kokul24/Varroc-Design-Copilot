"""
ml/utils.py — Shared utilities for the ML pipeline.

Contains:
- Numerically stable sigmoid
- Continuous penalty scoring functions
- Feature interaction computation
- Input validation and clamping
- Engineering threshold constants
"""

import math
import numpy as np

# ============================================================
# Engineering Thresholds (industry-standard DFM values)
# ============================================================
THRESHOLDS = {
    "min_wall_thickness": 1.0,       # mm — minimum safe wall thickness
    "max_wall_thickness": 8.0,       # mm — maximum before sink marks
    "min_draft_angle": 1.5,          # degrees — minimum for clean ejection
    "min_corner_radius": 0.5,        # mm — minimum to avoid stress concentrations
    "max_aspect_ratio": 8.0,         # ratio — maximum before warping risk
    "min_wall_uniformity": 0.6,      # 0-1 — minimum for uniform cooling
}

# Penalty weights for continuous scoring
PENALTY_WEIGHTS = {
    "w_wall": 0.30,           # wall thickness penalty weight
    "w_draft": 0.20,          # draft angle penalty weight
    "w_corner": 0.10,         # corner radius penalty weight
    "w_ar": 0.15,             # aspect ratio penalty weight
    "w_undercut": 0.10,       # undercut penalty weight
    "w_uniformity": 0.15,     # wall uniformity penalty weight
    "w_interaction": 0.20,    # feature interaction penalty weight
}

# Safe engineering bounds for clamping extreme inputs
SAFE_BOUNDS = {
    "wall_thickness": (0.1, 50.0),
    "draft_angle": (0.0, 30.0),
    "corner_radius": (0.0, 20.0),
    "aspect_ratio": (1.0, 50.0),
    "undercut_present": (0, 1),
    "wall_uniformity": (0.0, 1.0),
}

# Material encoding lookup
MATERIAL_ENCODING = {
    "abs": 0,
    "pc": 1,
    "pp": 2,
    "nylon": 3,
    "tpu": 4,
    # Legacy aliases from the existing codebase
    "aluminum": 5,
    "steel": 6,
    "titanium": 7,
    "plastic_abs": 0,
    "plastic_nylon": 3,
    "copper": 8,
    "brass": 9,
    "stainless_steel": 6,
}

# Reverse mapping for display
MATERIAL_LABELS = {
    0: "ABS",
    1: "PC",
    2: "PP",
    3: "Nylon",
    4: "TPU",
    5: "Aluminum",
    6: "Steel",
    7: "Titanium",
    8: "Copper",
    9: "Brass",
}


def stable_sigmoid(x: float) -> float:
    """
    Numerically stable sigmoid function.
    Prevents overflow for large positive/negative values.

    Args:
        x: Input value

    Returns:
        Sigmoid output in [0, 1]
    """
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    else:
        z = math.exp(x)
        return z / (1.0 + z)


def compute_continuous_penalties(features: dict) -> dict:
    """
    Compute continuous mathematical penalties for each DFM feature.

    Uses the formulae:
        penalty_wall = w1 * max(0, (min_wall - wall) / min_wall)
        penalty_draft = w2 * max(0, (min_draft - draft) / min_draft)
        penalty_ar = w3 * max(0, (aspect_ratio - threshold_ar) / threshold_ar)
        etc.

    Args:
        features: Dictionary of manufacturing features

    Returns:
        Dictionary with individual penalties, total penalty, and computed risk score
    """
    wall = features.get("wall_thickness", 0.0)
    draft = features.get("draft_angle", 0.0)
    corner = features.get("corner_radius", 0.0)
    ar = features.get("aspect_ratio", 1.0)
    undercut = features.get("undercut_present", 0)
    uniformity = features.get("wall_uniformity", 1.0)

    t = THRESHOLDS
    w = PENALTY_WEIGHTS

    # --- Individual penalties (all ≥ 0) ---
    # Wall thickness: penalize when below minimum
    min_wall = t["min_wall_thickness"]
    penalty_wall = w["w_wall"] * max(0.0, (min_wall - wall) / max(min_wall, 1e-8))

    # Also penalize excessively thick walls (secondary penalty)
    max_wall = t["max_wall_thickness"]
    if wall > max_wall:
        penalty_wall += w["w_wall"] * 0.3 * ((wall - max_wall) / max(max_wall, 1e-8))

    # Draft angle: penalize when below minimum
    min_draft = t["min_draft_angle"]
    penalty_draft = w["w_draft"] * max(0.0, (min_draft - draft) / max(min_draft, 1e-8))

    # Corner radius: penalize when below minimum
    min_corner = t["min_corner_radius"]
    penalty_corner = w["w_corner"] * max(0.0, (min_corner - corner) / max(min_corner, 1e-8))

    # Aspect ratio: penalize when above threshold
    threshold_ar = t["max_aspect_ratio"]
    penalty_ar = w["w_ar"] * max(0.0, (ar - threshold_ar) / max(threshold_ar, 1e-8))

    # Undercut: binary penalty
    penalty_undercut = w["w_undercut"] * float(undercut)

    # Wall uniformity: penalize when below minimum
    min_uniform = t["min_wall_uniformity"]
    penalty_uniformity = w["w_uniformity"] * max(0.0, (min_uniform - uniformity) / max(min_uniform, 1e-8))

    # --- Feature interaction penalty ---
    interaction_penalty = compute_interaction_penalty(features)

    # --- Total penalty ---
    total_penalty = (
        penalty_wall
        + penalty_draft
        + penalty_corner
        + penalty_ar
        + penalty_undercut
        + penalty_uniformity
        + interaction_penalty
    )

    # --- Risk score via sigmoid ---
    # Scale total_penalty so sigmoid gives meaningful spread
    # A penalty of ~1.0 maps to ~73 risk, ~2.0 maps to ~88 risk
    risk_score = stable_sigmoid(total_penalty * 3.0) * 100.0
    risk_score = max(0.0, min(100.0, risk_score))  # Clamp [0, 100]

    return {
        "penalty_wall": round(penalty_wall, 4),
        "penalty_draft": round(penalty_draft, 4),
        "penalty_corner": round(penalty_corner, 4),
        "penalty_ar": round(penalty_ar, 4),
        "penalty_undercut": round(penalty_undercut, 4),
        "penalty_uniformity": round(penalty_uniformity, 4),
        "interaction_penalty": round(interaction_penalty, 4),
        "total_penalty": round(total_penalty, 4),
        "risk_score": round(risk_score, 2),
    }


def compute_interaction_penalty(features: dict) -> float:
    """
    Compute feature interaction penalties.

    Key interactions:
    1. Thin wall + high aspect ratio → amplified warping risk
    2. Low draft angle + undercut → major ejection problems
    3. Poor uniformity + thin wall → differential cooling failure

    Args:
        features: Dictionary of manufacturing features

    Returns:
        Interaction penalty value (≥ 0)
    """
    wall = features.get("wall_thickness", 0.0)
    draft = features.get("draft_angle", 0.0)
    ar = features.get("aspect_ratio", 1.0)
    undercut = features.get("undercut_present", 0)
    uniformity = features.get("wall_uniformity", 1.0)

    t = THRESHOLDS
    w_int = PENALTY_WEIGHTS["w_interaction"]
    interaction = 0.0

    # Interaction 1: thin wall + high aspect ratio
    if wall < t["min_wall_thickness"] and ar > t["max_aspect_ratio"]:
        severity = ((t["min_wall_thickness"] - wall) / t["min_wall_thickness"]) * \
                   ((ar - t["max_aspect_ratio"]) / t["max_aspect_ratio"])
        interaction += w_int * min(severity, 1.0)

    # Interaction 2: low draft angle + undercut present
    if draft < t["min_draft_angle"] and undercut == 1:
        severity = (t["min_draft_angle"] - draft) / t["min_draft_angle"]
        interaction += w_int * 0.5 * severity

    # Interaction 3: poor uniformity + thin wall
    if uniformity < t["min_wall_uniformity"] and wall < t["min_wall_thickness"]:
        severity = ((t["min_wall_uniformity"] - uniformity) / t["min_wall_uniformity"]) * \
                   ((t["min_wall_thickness"] - wall) / t["min_wall_thickness"])
        interaction += w_int * 0.4 * min(severity, 1.0)

    return interaction


def clamp_features(features: dict) -> dict:
    """
    Clamp feature values to safe engineering bounds.
    Prevents unrealistic values from causing numerical issues.

    Args:
        features: Raw feature dictionary

    Returns:
        Clamped feature dictionary
    """
    clamped = features.copy()
    for key, (lo, hi) in SAFE_BOUNDS.items():
        if key in clamped:
            val = clamped[key]
            if isinstance(val, (int, float)):
                clamped[key] = max(lo, min(hi, val))
    return clamped


def encode_material(material: str) -> int:
    """
    Encode a material string to its numerical representation.

    Args:
        material: Material name (case-insensitive)

    Returns:
        Integer encoding
    """
    key = material.lower().strip().replace(" ", "_")
    return MATERIAL_ENCODING.get(key, 0)


def validate_input_features(features: dict) -> dict:
    """
    Validate and sanitize input features for inference.

    Raises:
        ValueError: If required fields are missing or have invalid types

    Returns:
        Validated and clamped feature dictionary
    """
    required_fields = [
        "wall_thickness", "draft_angle", "corner_radius",
        "aspect_ratio", "undercut_present", "wall_uniformity",
    ]

    # Check for missing fields
    missing = [f for f in required_fields if f not in features]
    if missing:
        raise ValueError(f"Missing required features: {missing}")

    # Check for valid types (must be numeric)
    for field in required_fields:
        val = features[field]
        if not isinstance(val, (int, float)):
            raise ValueError(
                f"Feature '{field}' must be numeric, got {type(val).__name__}: {val}"
            )
        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"Feature '{field}' has invalid value: {val}")

    # Check for negative values where invalid
    non_negative_fields = [
        "wall_thickness", "draft_angle", "corner_radius",
        "aspect_ratio", "wall_uniformity",
    ]
    for field in non_negative_fields:
        if features[field] < 0:
            raise ValueError(f"Feature '{field}' cannot be negative: {features[field]}")

    # Clamp to safe bounds
    clamped = clamp_features(features)

    return clamped


def get_risk_label(risk_score: float) -> str:
    """Map a risk score to a categorical label."""
    if risk_score < 40:
        return "LOW"
    elif risk_score <= 70:
        return "MEDIUM"
    else:
        return "HIGH"


def compute_confidence(
    model_probability: float = None,
    penalty_magnitude: float = None,
) -> float:
    """
    Compute a confidence score for the prediction.

    Uses model probability if available, otherwise derives
    from penalty magnitude.

    Returns:
        Confidence value in [0, 1]
    """
    if model_probability is not None:
        # Higher confidence when probability is further from 0.5
        confidence = abs(2.0 * model_probability - 1.0)
        # Smooth it so borderline cases show lower confidence
        confidence = 0.5 + 0.5 * confidence
    elif penalty_magnitude is not None:
        # Normalize penalty: high penalty → high confidence of risk
        confidence = stable_sigmoid(penalty_magnitude * 2.0)
    else:
        confidence = 0.5  # No information → neutral confidence

    return round(max(0.0, min(1.0, confidence)), 4)
