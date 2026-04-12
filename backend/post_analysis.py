"""
post_analysis.py — Post-inference modules for interpretability and business impact.

These helpers run only after prediction, SHAP, and violation checks are complete.
"""

from __future__ import annotations

import math
from typing import Any

from ml.utils import THRESHOLDS

_FEATURE_LABELS = {
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

_DEFAULT_ISSUES = [
    "Wall thickness",
    "Draft angle",
    "Aspect ratio",
]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(num) or math.isinf(num):
        return default
    return num


def _extract_shap_map(shap_values: Any) -> dict[str, float]:
    if isinstance(shap_values, dict) and isinstance(shap_values.get("shap_values"), dict):
        raw = shap_values["shap_values"]
    elif isinstance(shap_values, dict):
        raw = shap_values
    else:
        return {}

    cleaned = {}
    for key, value in raw.items():
        if key is None:
            continue
        cleaned[str(key)] = _safe_float(value, 0.0)
    return cleaned


def _fallback_penalty_map(fallback_penalties: dict | None) -> dict[str, float]:
    penalties = fallback_penalties or {}
    return {
        "wall_thickness": abs(_safe_float(penalties.get("penalty_wall"))),
        "draft_angle": abs(_safe_float(penalties.get("penalty_draft"))),
        "corner_radius": abs(_safe_float(penalties.get("penalty_corner"))),
        "aspect_ratio": abs(_safe_float(penalties.get("penalty_ar"))),
        "undercut_present": abs(_safe_float(penalties.get("penalty_undercut"))),
        "wall_uniformity": abs(_safe_float(penalties.get("penalty_uniformity"))),
        "wall_ar_interaction": abs(_safe_float(penalties.get("interaction_penalty"))) * 0.5,
        "draft_undercut_interaction": abs(_safe_float(penalties.get("interaction_penalty"))) * 0.3,
        "wall_uniformity_interaction": abs(_safe_float(penalties.get("interaction_penalty"))) * 0.2,
    }


def _normalize_issue_percentages(items: list[tuple[str, float]], limit: int = 3) -> list[dict]:
    selected = list(items[:limit])

    for default_feature in _DEFAULT_ISSUES:
        if len(selected) >= limit:
            break
        if default_feature not in [name for name, _ in selected]:
            selected.append((default_feature, 0.01))

    if not selected:
        selected = [(name, 0.01) for name in _DEFAULT_ISSUES]

    total = sum(abs(value) for _, value in selected)
    if total <= 0:
        total = 1.0

    pcts = []
    for feature_name, value in selected:
        pct = int(round((abs(value) / total) * 100))
        pcts.append({"feature": feature_name, "impact_pct": max(0, pct)})

    # Keep percentage sum around 100 by adjusting the largest contributor.
    diff = 100 - sum(item["impact_pct"] for item in pcts)
    if pcts:
        max_idx = max(range(len(pcts)), key=lambda idx: pcts[idx]["impact_pct"])
        pcts[max_idx]["impact_pct"] = max(0, pcts[max_idx]["impact_pct"] + diff)

    return pcts[:limit]


def compute_top_issues(shap_values: dict | None, fallback_penalties: dict | None) -> list[dict]:
    """
    Return top 3 risk factors with impact percentages.

    Priority:
    1) SHAP absolute contributions
    2) Penalty-based fallback contributions
    """
    shap_map = _extract_shap_map(shap_values)

    ranked: list[tuple[str, float]] = []
    if shap_map and any(abs(v) > 1e-9 for v in shap_map.values()):
        ranked = sorted(
            [
                (_FEATURE_LABELS.get(key, str(key).replace("_", " ").title()), abs(value))
                for key, value in shap_map.items()
            ],
            key=lambda x: x[1],
            reverse=True,
        )
    else:
        penalty_map = _fallback_penalty_map(fallback_penalties)
        ranked = sorted(
            [
                (_FEATURE_LABELS.get(key, str(key).replace("_", " ").title()), abs(value))
                for key, value in penalty_map.items()
            ],
            key=lambda x: x[1],
            reverse=True,
        )

    return _normalize_issue_percentages(ranked, limit=3)


def compute_cost_impact(features: dict | None, violations: list | None) -> tuple[int, list[str]]:
    """
    Compute rule-based estimated manufacturing cost impact from detected issues.
    """
    feats = features or {}
    issues = violations or []

    max_wall = THRESHOLDS.get("max_wall_thickness", 8.0)
    min_draft = THRESHOLDS.get("min_draft_angle", 1.5)
    uniformity_threshold = THRESHOLDS.get("min_wall_uniformity", 0.6)

    wall_thickness = _safe_float(feats.get("wall_thickness"), 0.0)
    draft_angle = _safe_float(feats.get("draft_angle"), 0.0)
    wall_uniformity = _safe_float(feats.get("wall_uniformity"), 1.0)
    undercut_present = int(_safe_float(feats.get("undercut_present"), 0.0)) == 1

    cost = 0
    reasons: list[str] = []

    if wall_thickness > max_wall:
        cost += 8000
        reasons.append("Excess wall thickness increases cycle time and material usage")

    if wall_uniformity < uniformity_threshold:
        cost += 5000
        reasons.append("Non-uniform walls cause defects and rework")

    if undercut_present:
        cost += 15000
        reasons.append("Undercuts require complex tooling")

    if draft_angle < min_draft:
        cost += 4000
        reasons.append("Insufficient draft increases ejection difficulty")

    if not reasons:
        if issues:
            reasons = [
                "Additional process tuning may be required based on detected DFM violations"
            ]
        else:
            reasons = ["Minimal additional tooling cost"]

    return max(0, int(cost)), reasons
