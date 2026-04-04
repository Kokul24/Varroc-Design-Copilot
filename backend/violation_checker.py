"""
violation_checker.py — Rule-based DFM (Design for Manufacturability) violation detection.
Checks extracted features against industry-standard manufacturing thresholds.
"""

# DFM rule thresholds
DFM_RULES = {
    "wall_thickness": {
        "min": 1.0,
        "max": 8.0,
        "unit": "mm",
        "severity_weight": 0.9,
    },
    "draft_angle": {
        "min": 1.5,
        "unit": "degrees",
        "severity_weight": 0.7,
    },
    "corner_radius": {
        "min": 0.5,
        "unit": "mm",
        "severity_weight": 0.6,
    },
    "aspect_ratio": {
        "max": 8.0,
        "severity_weight": 0.5,
    },
    "wall_uniformity": {
        "min": 0.6,
        "severity_weight": 0.8,
    },
}


def check_violations(features: dict) -> list:
    """
    Check extracted features against DFM rules.

    Args:
        features: Dictionary of extracted manufacturing features

    Returns:
        List of violation dictionaries with type, message, severity, and suggestion
    """
    violations = []

    # --- Wall Thickness ---
    wt = features.get("wall_thickness", 0)
    rule = DFM_RULES["wall_thickness"]
    if wt < rule["min"]:
        violations.append({
            "type": "CRITICAL",
            "feature": "wall_thickness",
            "message": f"Wall thickness ({wt} mm) is below minimum threshold ({rule['min']} mm)",
            "detail": "Thin walls increase risk of warping, sink marks, and structural failure during manufacturing.",
            "suggestion": f"Increase wall thickness to at least {rule['min']} mm. Recommended range: {rule['min']}–{rule['max']} mm.",
            "severity": round(rule["severity_weight"] * (1 - wt / rule["min"]) * 100, 1),
        })
    elif wt > rule["max"]:
        violations.append({
            "type": "WARNING",
            "feature": "wall_thickness",
            "message": f"Wall thickness ({wt} mm) exceeds recommended maximum ({rule['max']} mm)",
            "detail": "Excessively thick walls can cause sink marks, voids, and longer cycle times.",
            "suggestion": f"Consider coring out thick sections. Target range: {rule['min']}–{rule['max']} mm.",
            "severity": round(rule["severity_weight"] * min((wt - rule["max"]) / rule["max"], 1.0) * 60, 1),
        })

    # --- Draft Angle ---
    da = features.get("draft_angle", 0)
    rule = DFM_RULES["draft_angle"]
    if da < rule["min"]:
        violations.append({
            "type": "CRITICAL" if da < 0.5 else "WARNING",
            "feature": "draft_angle",
            "message": f"Draft angle ({da}°) is below minimum ({rule['min']}°)",
            "detail": "Insufficient draft angle makes part ejection difficult, causing surface damage and tool wear.",
            "suggestion": f"Increase draft angle to at least {rule['min']}°. Use 2°–3° for textured surfaces.",
            "severity": round(rule["severity_weight"] * (1 - da / rule["min"]) * 100, 1),
        })

    # --- Corner Radius ---
    cr = features.get("corner_radius", 0)
    rule = DFM_RULES["corner_radius"]
    if cr < rule["min"]:
        violations.append({
            "type": "WARNING",
            "feature": "corner_radius",
            "message": f"Corner radius ({cr} mm) is too small (min: {rule['min']} mm)",
            "detail": "Sharp corners create stress concentrations leading to cracking and poor material flow.",
            "suggestion": f"Add fillets with radius ≥ {rule['min']} mm. Use 50–75% of wall thickness as radius.",
            "severity": round(rule["severity_weight"] * (1 - cr / rule["min"]) * 100, 1),
        })

    # --- Aspect Ratio ---
    ar = features.get("aspect_ratio", 0)
    rule = DFM_RULES["aspect_ratio"]
    if ar > rule["max"]:
        violations.append({
            "type": "WARNING",
            "feature": "aspect_ratio",
            "message": f"Aspect ratio ({ar}) exceeds recommended limit ({rule['max']})",
            "detail": "High aspect ratios increase warping risk and complicate mold filling uniformity.",
            "suggestion": f"Redesign to reduce aspect ratio below {rule['max']}. Consider splitting into sub-assemblies.",
            "severity": round(rule["severity_weight"] * min((ar - rule["max"]) / rule["max"], 1.0) * 80, 1),
        })

    # --- Undercut ---
    if features.get("undercut_present", 0) == 1:
        violations.append({
            "type": "INFO",
            "feature": "undercut_present",
            "message": "Undercut geometry detected",
            "detail": "Undercuts require side actions or lifters in tooling, increasing mold complexity and cost.",
            "suggestion": "Evaluate if undercuts can be eliminated through redesign. If required, plan for slide mechanisms.",
            "severity": 40.0,
        })

    # --- Wall Uniformity ---
    wu = features.get("wall_uniformity", 0)
    rule = DFM_RULES["wall_uniformity"]
    if wu < rule["min"]:
        violations.append({
            "type": "WARNING",
            "feature": "wall_uniformity",
            "message": f"Wall uniformity ({wu}) is below threshold ({rule['min']})",
            "detail": "Non-uniform walls cause differential cooling, leading to warping, sink marks, and residual stress.",
            "suggestion": f"Aim for uniform wall thickness (uniformity ≥ {rule['min']}). Gradually transition between thick and thin sections.",
            "severity": round(rule["severity_weight"] * (1 - wu / rule["min"]) * 100, 1),
        })

    # Sort by severity (highest first)
    violations.sort(key=lambda v: v.get("severity", 0), reverse=True)

    return violations
