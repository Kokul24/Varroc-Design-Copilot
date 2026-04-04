"""
recommendation_engine.py — Generate human-readable AI recommendations.
Uses LLM API (OpenAI) if available, otherwise falls back to template-based generation.
The LLM is ONLY used for converting structured data into natural language —
NOT for feature extraction, risk scoring, or prediction.
"""

import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def generate_recommendation(
    features: dict,
    risk_score: float,
    risk_label: str,
    violations: list,
    shap_values: dict,
    material: str,
) -> dict:
    """
    Generate actionable engineering recommendations.

    Tries LLM API first, falls back to template-based generation.

    Returns:
        Dictionary with 'summary', 'recommendations' list, and 'source' ('llm' or 'template')
    """
    # Try LLM-based generation first
    if OPENAI_API_KEY:
        try:
            result = _generate_with_llm(
                features, risk_score, risk_label, violations, shap_values, material
            )
            if result:
                return result
        except Exception as e:
            print(f"[recommendation_engine] LLM generation failed: {e}")

    # Fallback to template-based generation
    return _generate_with_template(
        features, risk_score, risk_label, violations, shap_values, material
    )


def _generate_with_llm(
    features, risk_score, risk_label, violations, shap_values, material
) -> dict:
    """Generate recommendations using OpenAI API."""
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)

    # Build structured context for the LLM
    violation_text = "\n".join(
        [f"- [{v['type']}] {v['message']}" for v in violations]
    ) or "No violations detected."

    # Get top contributing features from SHAP
    sorted_shap = sorted(
        shap_values.get("shap_values", {}).items(),
        key=lambda x: abs(x[1]),
        reverse=True,
    )
    top_features = sorted_shap[:3]
    shap_text = "\n".join(
        [f"- {name}: contribution = {val:+.4f}" for name, val in top_features]
    )

    prompt = f"""You are a manufacturing engineering expert. Based on the following DFM (Design for Manufacturability) analysis results, provide a clear, actionable engineering summary and recommendations.

## Analysis Results
- **Material**: {material}
- **Risk Score**: {risk_score}/100 ({risk_label})

## Key Features
- Wall Thickness: {features.get('wall_thickness', 'N/A')} mm
- Draft Angle: {features.get('draft_angle', 'N/A')}°
- Corner Radius: {features.get('corner_radius', 'N/A')} mm
- Aspect Ratio: {features.get('aspect_ratio', 'N/A')}
- Undercut Present: {'Yes' if features.get('undercut_present') else 'No'}
- Wall Uniformity: {features.get('wall_uniformity', 'N/A')}

## Detected Violations
{violation_text}

## Top Contributing Factors (SHAP Analysis)
{shap_text}

Provide your response as:
1. A brief executive summary (2-3 sentences)
2. A numbered list of 3-5 specific, actionable recommendations

Focus on practical manufacturing improvements. Be specific about values and tolerances."""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a DFM expert providing manufacturing recommendations."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=800,
    )

    content = response.choices[0].message.content

    # Parse the response into summary and recommendations
    lines = content.strip().split("\n")
    summary_lines = []
    recommendations = []
    in_recommendations = False

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith(("1.", "2.", "3.", "4.", "5.")):
            in_recommendations = True
            # Remove the number prefix
            rec_text = line.split(".", 1)[1].strip() if "." in line else line
            recommendations.append(rec_text)
        elif in_recommendations and line.startswith(("-", "•", "*")):
            recommendations.append(line.lstrip("-•* ").strip())
        elif not in_recommendations:
            summary_lines.append(line)

    return {
        "summary": " ".join(summary_lines) if summary_lines else content[:200],
        "recommendations": recommendations if recommendations else [content],
        "source": "llm",
    }


def _generate_with_template(
    features, risk_score, risk_label, violations, shap_values, material
) -> dict:
    """Generate recommendations using rule-based templates."""
    recommendations = []

    # Summary based on risk level
    if risk_label == "LOW":
        summary = (
            f"This {material} part design shows low manufacturing risk (score: {risk_score}/100). "
            f"The design generally follows DFM best practices with minor areas for optimization."
        )
    elif risk_label == "MEDIUM":
        summary = (
            f"This {material} part design has moderate manufacturing risk (score: {risk_score}/100). "
            f"Several design parameters are near threshold limits and should be reviewed before production."
        )
    else:
        summary = (
            f"This {material} part design presents high manufacturing risk (score: {risk_score}/100). "
            f"Critical DFM violations were detected that must be addressed to ensure producibility."
        )

    # Feature-specific recommendations
    wt = features.get("wall_thickness", 0)
    if wt < 1.0:
        recommendations.append(
            f"**Increase wall thickness** from {wt} mm to at least 1.0 mm. "
            f"For {material}, recommended minimum is 1.0–1.5 mm to prevent warping and ensure structural integrity."
        )
    elif wt > 8.0:
        recommendations.append(
            f"**Reduce wall thickness** from {wt} mm. Consider coring out thick sections to "
            f"maintain thickness between 1.0–8.0 mm, reducing material usage and cycle time."
        )

    da = features.get("draft_angle", 0)
    if da < 1.5:
        recommendations.append(
            f"**Increase draft angle** from {da}° to at least 1.5°. "
            f"For textured surfaces on {material} parts, use 2°–3° to facilitate clean part ejection."
        )

    cr = features.get("corner_radius", 0)
    if cr < 0.5:
        recommendations.append(
            f"**Add fillets** to sharp corners (current radius: {cr} mm). "
            f"Use a minimum radius of 0.5 mm (ideally 50–75% of wall thickness) to reduce stress concentrations."
        )

    ar = features.get("aspect_ratio", 0)
    if ar > 8.0:
        recommendations.append(
            f"**Reduce aspect ratio** from {ar}:1 to below 8:1. "
            f"Consider adding ribs for stiffness or splitting into sub-assemblies to improve moldability."
        )

    if features.get("undercut_present") == 1:
        recommendations.append(
            f"**Evaluate undercut geometry** — undercuts require side-action tooling, increasing mold cost by 15–30%. "
            f"If possible, redesign to eliminate undercuts or use snap-fit alternatives."
        )

    wu = features.get("wall_uniformity", 0)
    if wu < 0.6:
        recommendations.append(
            f"**Improve wall uniformity** (current: {wu}, target: ≥0.6). "
            f"Gradual transitions between thick and thin sections reduce warping and internal stress in {material} parts."
        )

    # Add SHAP-based insight
    shap_vals = shap_values.get("shap_values", {})
    if shap_vals:
        sorted_shap = sorted(shap_vals.items(), key=lambda x: abs(x[1]), reverse=True)
        top_feature = sorted_shap[0]
        labels = shap_values.get("feature_labels", {})
        feature_label = labels.get(top_feature[0], top_feature[0])
        direction = "increasing" if top_feature[1] > 0 else "decreasing"
        recommendations.append(
            f"**Priority focus: {feature_label}** — AI analysis shows this feature has the highest impact "
            f"on risk score ({direction} risk). Optimizing this parameter will have the greatest effect on manufacturability."
        )

    # Ensure at least some recommendations
    if not recommendations:
        recommendations.append(
            "Design parameters are within acceptable ranges. Consider minor optimizations "
            "to further reduce manufacturing costs and improve cycle time."
        )
        recommendations.append(
            "Run a mold flow simulation to verify gate placement and cooling channel design."
        )

    return {
        "summary": summary,
        "recommendations": recommendations,
        "source": "template",
    }
