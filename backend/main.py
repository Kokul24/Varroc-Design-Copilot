"""
main.py — FastAPI backend for CADguard.
Handles file uploads, CAD analysis, and serves results.
"""

import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import internal modules
from model_loader import predict
from feature_extractor import extract_features, get_material_list
from violation_checker import check_violations
from shap_explainer import compute_shap_values
from recommendation_engine import generate_recommendation
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
    description="AI-powered CAD validation and DFM analysis",
    version="1.0.0",
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


# --- Health Check ---
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "CADguard API"}


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
    3. Predict risk score
    4. Compute SHAP values
    5. Check DFM violations
    6. Generate recommendations
    7. Store in database
    8. Return complete results
    """
    try:
        # 1. Read file bytes
        file_bytes = await file.read()
        filename = file.filename or "unnamed_file"

        # 2. Extract features
        features = extract_features(file_bytes, filename, material)

        # 3. Predict risk
        prediction = predict(features)
        risk_score = prediction["risk_score"]
        risk_label = prediction["risk_label"]

        # 4. Compute SHAP values
        shap_result = compute_shap_values(features)

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

        # 7. Store in database
        stored = store_analysis(
            file_name=filename,
            material=material,
            risk_score=risk_score,
            risk_label=risk_label,
            features=features,
            violations=violations,
            shap_values=shap_result,
            recommendations=recommendation,
        )

        # 8. Return complete response
        return {
            "id": stored.get("id"),
            "file_name": filename,
            "material": material,
            "risk_score": risk_score,
            "risk_label": risk_label,
            "probability": prediction["probability"],
            "features": features,
            "violations": violations,
            "shap_values": shap_result,
            "recommendations": recommendation,
            "created_at": stored.get("created_at"),
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
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


# --- Run Server ---
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host=host, port=port, reload=True)
