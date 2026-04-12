"""
chat_engine.py — Gemini-powered conversational Q&A for DFM analysis.

Provides context-aware answers about analysis violations, features,
and manufacturing best practices using the Google Gemini API.
"""

import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def _build_system_context(analysis_data: dict) -> str:
    """
    Build a rich system prompt from the analysis data so Gemini can
    answer questions with full knowledge of the specific part.
    """
    features = analysis_data.get("features", {})
    violations = analysis_data.get("violations", [])
    recommendations = analysis_data.get("recommendations", {})
    risk_score = analysis_data.get("risk_score", "N/A")
    risk_label = analysis_data.get("risk_label", "N/A")
    material = analysis_data.get("material", "N/A")
    file_name = analysis_data.get("file_name", "Unknown")

    # Format violations
    violation_text = ""
    if violations:
        for i, v in enumerate(violations, 1):
            violation_text += (
                f"\n  {i}. [{v.get('type', 'INFO')}] {v.get('message', '')}\n"
                f"     Detail: {v.get('detail', 'N/A')}\n"
                f"     Suggested Fix: {v.get('suggestion', 'N/A')}\n"
                f"     Severity: {v.get('severity', 0)}\n"
            )
    else:
        violation_text = "\n  No violations detected."

    # Format recommendations
    rec_text = ""
    if isinstance(recommendations, dict):
        summary = recommendations.get("summary", "")
        rec_list = recommendations.get("recommendations", [])
        if summary:
            rec_text += f"\n  Summary: {summary}\n"
        for i, r in enumerate(rec_list, 1):
            rec_text += f"  {i}. {r}\n"
    elif isinstance(recommendations, list):
        for i, r in enumerate(recommendations, 1):
            rec_text += f"  {i}. {r}\n"

    # Format features
    feature_text = ""
    feature_labels = {
        "wall_thickness": ("Wall Thickness", "mm"),
        "draft_angle": ("Draft Angle", "°"),
        "corner_radius": ("Corner Radius", "mm"),
        "aspect_ratio": ("Aspect Ratio", ""),
        "wall_uniformity": ("Wall Uniformity", ""),
        "undercut_present": ("Undercut Present", ""),
    }
    for key, (label, unit) in feature_labels.items():
        val = features.get(key)
        if val is not None:
            if key == "undercut_present":
                display = "Yes" if val == 1 else "No"
            else:
                display = f"{val} {unit}".strip()
            feature_text += f"  - {label}: {display}\n"

    # SHAP values
    shap_data = analysis_data.get("shap_values", {})
    shap_vals = shap_data.get("shap_values", {}) if isinstance(shap_data, dict) else {}
    shap_text = ""
    if shap_vals:
        sorted_shap = sorted(shap_vals.items(), key=lambda x: abs(x[1]), reverse=True)
        for name, val in sorted_shap[:5]:
            label = feature_labels.get(name, (name, ""))[0]
            direction = "increases" if val > 0 else "decreases"
            shap_text += f"  - {label}: {val:+.4f} ({direction} risk)\n"

    return f"""You are an expert manufacturing engineer and DFM (Design for Manufacturability) consultant embedded in the Varroc DesignCopilot AI system. You are helping a user understand and fix the issues found in their CAD part analysis.

## ANALYSIS CONTEXT
- **File**: {file_name}
- **Material**: {material}
- **Risk Score**: {risk_score}/100
- **Risk Label**: {risk_label}

## EXTRACTED FEATURES
{feature_text}

## DFM VIOLATIONS DETECTED
{violation_text}

## AI RECOMMENDATIONS
{rec_text}

## SHAP FEATURE CONTRIBUTIONS (impact on risk)
{shap_text}

## YOUR ROLE
1. Answer questions about the specific violations, features, and recommendations shown above.
2. Provide actionable, specific engineering advice on how to fix each issue.
3. Explain WHY certain features are problematic in manufacturing (injection molding, casting, etc.).
4. Suggest specific numerical values, tolerances, and design changes.
5. Reference industry standards (e.g., DFM guidelines for {material}) when relevant.
6. If the user asks about something not related to this analysis, politely redirect them.
7. Keep answers concise but thorough — aim for 2-4 paragraphs max.
8. Use bullet points for actionable steps.
9. Always be encouraging — help the user improve their design, don't just criticize.

IMPORTANT: You have full context of the part analysis. Use the specific feature values and violations listed above in your answers. Do NOT make up data that contradicts the analysis."""


def chat_with_gemini(
    user_message: str,
    analysis_data: dict,
    conversation_history: list[dict] | None = None,
) -> str:
    """
    Send a message to Gemini with full analysis context.

    Args:
        user_message: The user's question
        analysis_data: The complete analysis record from the database
        conversation_history: Optional list of prior messages
            [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

    Returns:
        The Gemini response text.

    Raises:
        ValueError: If the API key is not configured.
        RuntimeError: If the Gemini call fails.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in the environment.")

    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)

    system_context = _build_system_context(analysis_data)

    # Build the conversation messages
    contents = []

    # Add conversation history if present
    if conversation_history:
        for msg in conversation_history:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [msg["content"]]})

    # Add the current user message
    contents.append({"role": "user", "parts": [user_message]})

    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash", 
            system_instruction=system_context,
            generation_config=genai.GenerationConfig(
                temperature=0.4,
                max_output_tokens=1024,
                top_p=0.9,
            ),
        )

        response = model.generate_content(contents)

        if response.text:
            return response.text
        else:
            return "I'm sorry, I couldn't generate a response. Please try rephrasing your question."

    except Exception as e:
        print(f"[chat_engine] Gemini API error: {e}")
        error_msg = str(e)
        if "403" in error_msg and "leaked" in error_msg:
            return "⚠️ **API Error:** Your Gemini API key has been flagged by Google as leaked and disabled. Please generate a new key from Google AI Studio and update your backend environment variables."
        raise RuntimeError(f"Gemini API call failed: {error_msg}")
