"""
main.py — FastAPI backend for CADguard.
Handles file uploads, CAD analysis, and serves results.

Integrates the production ML pipeline for:
- Continuous risk scoring (penalty + ML blend)
- SHAP-based explainability
- Top failure reason ranking
- Confidence scoring
- Feature interaction handling
"""

import os
import sys
import json
import time
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend dir to path for ml package imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import internal modules
from model_loader import predict
from feature_extractor import extract_features, get_material_list
from violation_checker import check_violations
from shap_explainer import compute_shap_values
from recommendation_engine import generate_recommendation
from pdf_generator import generate_analysis_pdf
from chat_engine import chat_with_gemini
from post_analysis import compute_top_issues, compute_cost_impact
from supabase_client import (
    store_analysis,
    get_analysis,
    get_recent_analyses,
    update_analysis,
    delete_analysis,
)
from auth_routes import router as auth_router, get_current_user

# --- App Setup ---
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]


app = FastAPI(
    title="CADguard API",
    description="AI-powered CAD validation and DFM analysis with explainable ML",
    version="2.0.0",
)

# CORS configuration for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


def _log_stl_model_io(filename: str, material: str, features: dict, prediction: dict) -> None:
    """
    Print a presentation-friendly terminal log for STL analysis.
    Shows model input features, calculation components, and final outputs.
    """
    ml_score = prediction.get("ml_risk_score")
    penalty_score = prediction.get("penalty_risk_score")
    blended_score = prediction.get("risk_score")
    penalty_breakdown = prediction.get("penalty_breakdown", {})

    calc_summary = {
        "blend_formula": "blended_risk = 0.7 * ml_risk + 0.3 * penalty_risk",
        "ml_risk_score": ml_score,
        "penalty_risk_score": penalty_score,
        "blended_risk_score": blended_score,
        "risk_probability": prediction.get("probability"),
        "confidence": prediction.get("confidence"),
        "penalty_breakdown": penalty_breakdown,
    }

    output_summary = {
        "risk_label": prediction.get("risk_label"),
        "top_issues": prediction.get("top_issues", []),
        "shap_values": prediction.get("shap_values", {}),
    }

    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "file_name": filename,
        "material": material,
        "model_input_features": features,
        "model_calculations": calc_summary,
        "model_output": output_summary,
    }

    print("\n" + "=" * 88)
    print("[CADguard][STL Upload] Model I/O and Calculations")
    print(json.dumps(payload, indent=2, default=str))
    print("=" * 88 + "\n", flush=True)


# --- Pydantic Models for Direct Analysis ---
class DirectAnalysisRequest(BaseModel):
    """Request model for direct feature analysis (no file upload)."""
    wall_thickness: float = Field(..., gt=0, description="Wall thickness in mm")
    draft_angle: float = Field(..., ge=0, description="Draft angle in degrees")
    corner_radius: float = Field(..., ge=0, description="Corner radius in mm")
    aspect_ratio: float = Field(..., gt=0, description="Aspect ratio")
    undercut_present: int = Field(..., ge=0, le=1, description="0 or 1")
    wall_uniformity: float = Field(..., ge=0, le=1, description="0 to 1")
    material: Optional[str] = Field(default="ABS", description="Material type")


# --- Health Check ---
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    model_status = "loaded"
    try:
        from model_loader import get_model
        get_model()
    except Exception:
        model_status = "not_loaded"

    return {
        "status": "healthy",
        "service": "CADguard API",
        "model_status": model_status,
        "version": "2.0.0",
    }


# --- Materials List ---
@app.get("/api/materials")
async def list_materials():
    """Return available materials for the dropdown selector."""
    return {"materials": get_material_list()}


# --- File Analysis (Main Pipeline) ---
@app.post("/api/analyze")
async def analyze_file(
    file: UploadFile = File(...),
    material: str = Form(default="aluminum"),
    current_user: dict = Depends(get_current_user),
):
    """
    Main analysis pipeline:
    1. Read uploaded file
    2. Extract/simulate features
    3. Predict risk score (ML + continuous scoring)
    4. Compute SHAP values
    5. Check DFM violations
    6. Generate recommendations
    7. Store in database
    8. Return complete results with explainability
    """
    try:
        # 1. Read file bytes
        file_bytes = await file.read()
        filename = file.filename or "unnamed_file"

        # 2. Extract features
        features = extract_features(file_bytes, filename, material)

        # 3. Predict risk (uses new ML pipeline with blended scoring)
        prediction = predict(features)
        risk_score = prediction["risk_score"]
        risk_label = prediction["risk_label"]

        # Terminal logging for presentation: show model inputs and outputs for STL uploads.
        if filename.lower().endswith(".stl"):
            _log_stl_model_io(filename, material, features, prediction)

        # 4. Compute SHAP values (prediction already contains SHAP,
        #    but we recompute for consistency with existing API)
        shap_result = {
            "shap_values": prediction.get("shap_values", {}),
            "base_value": prediction.get("shap_base_value", 0.0),
            "feature_values": prediction.get("features", features),
            "feature_labels": {
                "wall_thickness": "Wall Thickness",
                "draft_angle": "Draft Angle",
                "corner_radius": "Corner Radius",
                "aspect_ratio": "Aspect Ratio",
                "undercut_present": "Undercut Present",
                "wall_uniformity": "Wall Uniformity",
                "material_encoded": "Material Type",
            },
        }

        # 5. Check violations
        violations = check_violations(features)

        # 6. Generate recommendations
        recommendation = generate_recommendation(
            features=features,
            risk_score=risk_score,
            risk_label=risk_label,
            violations=violations,
            shap_values=shap_result,
            material=material,
        )

        # 7. Post-analysis modules (run only after prediction + SHAP + violations)
        top_issues = compute_top_issues(
            shap_values=shap_result,
            fallback_penalties=prediction.get("penalty_breakdown", {}),
        )
        estimated_cost_impact, cost_breakdown = compute_cost_impact(
            features=features,
            violations=violations,
        )

        # 8. Store in database
        stored = store_analysis(
            file_name=filename,
            material=material,
            risk_score=risk_score,
            risk_label=risk_label,
            confidence=prediction.get("confidence", 0.5),
            features=features,
            violations=violations,
            shap_values=shap_result,
            recommendations=recommendation,
            top_issues=top_issues,
            estimated_cost_impact=estimated_cost_impact,
            cost_breakdown=cost_breakdown,
        )

        # 9. Return complete response with all ML pipeline outputs
        return {
            "id": stored.get("id"),
            "file_name": filename,
            "material": material,
            "risk_score": risk_score,
            "risk_label": risk_label,
            "probability": prediction["probability"],
            "confidence": prediction.get("confidence", 0.5),
            "top_issues": top_issues,
            "features": features,
            "violations": violations,
            "shap_values": shap_result,
            "recommendations": recommendation,
            "estimated_cost_impact": estimated_cost_impact,
            "cost_breakdown": cost_breakdown,
            "penalty_breakdown": prediction.get("penalty_breakdown", {}),
            "created_at": stored.get("created_at"),
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


# --- Direct Analysis (no file upload) ---
@app.post("/api/analyze/direct")
async def analyze_direct(
    request: DirectAnalysisRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Analyze manufacturing features directly (without file upload).

    Accepts feature values directly and returns:
    - risk_score (0-100)
    - risk_label (LOW/MEDIUM/HIGH)
    - confidence (0-1)
    - top_issues (ranked failure reasons)
    - shap_values (feature contributions)
    - penalty_breakdown (continuous scoring details)
    """
    try:
        features = {
            "wall_thickness": request.wall_thickness,
            "draft_angle": request.draft_angle,
            "corner_radius": request.corner_radius,
            "aspect_ratio": request.aspect_ratio,
            "undercut_present": request.undercut_present,
            "wall_uniformity": request.wall_uniformity,
            "material": request.material,
        }

        # Run full prediction pipeline
        prediction = predict(features)

        # Check violations
        features_for_violations = features.copy()
        features_for_violations["material_encoded"] = prediction["features"].get(
            "material_encoded", 0
        )
        violations = check_violations(features_for_violations)

        top_issues = compute_top_issues(
            shap_values=prediction.get("shap_values", {}),
            fallback_penalties=prediction.get("penalty_breakdown", {}),
        )
        estimated_cost_impact, cost_breakdown = compute_cost_impact(
            features=prediction.get("features", features),
            violations=violations,
        )

        return {
            "risk_score": prediction["risk_score"],
            "risk_label": prediction["risk_label"],
            "probability": prediction["probability"],
            "confidence": prediction.get("confidence", 0.5),
            "top_issues": top_issues,
            "shap_values": prediction.get("shap_values", {}),
            "features": prediction.get("features", features),
            "violations": violations,
            "estimated_cost_impact": estimated_cost_impact,
            "cost_breakdown": cost_breakdown,
            "penalty_breakdown": prediction.get("penalty_breakdown", {}),
        }

    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Model not available: {str(e)}. Run 'python -m ml.train' first."
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


# --- Get Single Analysis ---
@app.get("/api/analyses/{analysis_id}")
async def get_analysis_by_id(analysis_id: str, current_user: dict = Depends(get_current_user)):
    """Retrieve a specific analysis by ID."""
    result = get_analysis(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return result


# --- Get Recent Analyses ---
@app.get("/api/analyses")
async def list_recent_analyses(limit: int = 10, current_user: dict = Depends(get_current_user)):
    """Retrieve recent analyses for the dashboard."""
    return {"analyses": get_recent_analyses(limit)}


# --- Update Analysis ---
@app.put("/api/analyses/{analysis_id}")
async def update_analysis_by_id(
    analysis_id: str,
    updates: dict,
    current_user: dict = Depends(get_current_user),
):
    """Update an analysis record by ID. Pass only the fields to change."""
    result = update_analysis(analysis_id, updates)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return result


# --- Delete Analysis ---
@app.delete("/api/analyses/{analysis_id}")
async def delete_analysis_by_id(analysis_id: str, current_user: dict = Depends(get_current_user)):
    """Delete an analysis record by ID."""
    deleted = delete_analysis(analysis_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"deleted": True, "id": analysis_id}


# --- Generate PDF Report ---
@app.get("/api/generate-pdf/{analysis_id}")
async def generate_pdf(analysis_id: str, current_user: dict = Depends(get_current_user)):
    """
    Generate and download a professional PDF report for a given analysis.

    Fetches the analysis record from the database, generates a formatted
    PDF using reportlab, and returns it as a downloadable file.
    """
    # 1. Fetch the analysis from DB
    analysis = get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    try:
        # 2. Generate the PDF
        pdf_path = generate_analysis_pdf(analysis)

        # 3. Build a readable filename
        file_name = analysis.get("file_name", "analysis")
        safe_name = "".join(
            c if c.isalnum() or c in ("_", "-", ".") else "_"
            for c in os.path.splitext(file_name)[0]
        )
        download_name = f"CADguard_Report_{safe_name}.pdf"

        # 4. Return as downloadable response
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=download_name,
            headers={
                "Content-Disposition": f'attachment; filename="{download_name}"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {str(e)}"
        )


# --- Conversational Q&A (Gemini) ---
class ChatMessage(BaseModel):
    """A single message in the conversation history."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request model for the chat endpoint."""
    message: str = Field(..., min_length=1, max_length=2000, description="User's question")
    history: list[ChatMessage] = Field(default=[], description="Prior conversation turns")


@app.post("/api/chat/{analysis_id}")
async def chat_about_analysis(
    analysis_id: str,
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Conversational Q&A powered by Gemini.

    Users can ask questions about faults, violations, and improvements
    for a specific analysis. Gemini responds with context-aware
    engineering advice.
    """
    # 1. Fetch the analysis to seed context
    analysis = get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # 2. Convert history to dicts
    history = [msg.model_dump() for msg in request.history]

    try:
        # 3. Call Gemini with full analysis context
        response_text = chat_with_gemini(
            user_message=request.message,
            analysis_data=analysis,
            conversation_history=history,
        )

        return {
            "response": response_text,
            "analysis_id": analysis_id,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Chat service not configured: {str(e)}"
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=502,
            detail=f"AI service error: {str(e)}"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Chat failed: {str(e)}"
        )


# --- Run Server ---
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host=host, port=port, reload=True)