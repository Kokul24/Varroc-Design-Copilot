"""
feature_extractor.py — Extract or simulate manufacturing features from CAD files.
Uses trimesh for basic geometry analysis on STL files, and simulates
DFM-relevant features that cannot be directly computed from mesh alone.
"""

import random
import numpy as np

# Material encoding lookup
MATERIAL_ENCODING = {
    "aluminum": 0,
    "steel": 1,
    "titanium": 2,
    "plastic_abs": 3,
    "plastic_nylon": 4,
    "copper": 5,
    "brass": 6,
    "stainless_steel": 7,
}


def extract_features(file_bytes: bytes, filename: str, material: str) -> dict:
    """
    Extract manufacturing features from an uploaded file.

    For STL files, uses trimesh for geometry analysis.
    For other files or when trimesh fails, simulates realistic features.

    Args:
        file_bytes: Raw bytes of the uploaded file
        filename: Original filename
        material: Material type string

    Returns:
        Dictionary of extracted/simulated features
    """
    features = None

    # Attempt trimesh extraction for STL files
    if filename.lower().endswith(".stl"):
        features = _extract_from_stl(file_bytes)

    # Fallback to simulation if extraction failed or non-STL file
    if features is None:
        features = _simulate_features(filename)

    # Add material encoding
    material_key = material.lower().replace(" ", "_")
    features["material_encoded"] = MATERIAL_ENCODING.get(material_key, 0)

    return features


def _extract_from_stl(file_bytes: bytes) -> dict:
    """Extract features from STL file using trimesh."""
    try:
        import trimesh
        import io

        mesh = trimesh.load(io.BytesIO(file_bytes), file_type="stl")

        if not hasattr(mesh, "bounds") or mesh.bounds is None:
            return None

        # Compute bounding box dimensions
        bounds = mesh.bounds
        dimensions = bounds[1] - bounds[0]
        sorted_dims = sorted(dimensions)

        # Aspect ratio from bounding box
        aspect_ratio = float(sorted_dims[2] / max(sorted_dims[0], 0.001))

        # Estimate wall thickness from mesh analysis
        # Use a heuristic: volume / surface_area gives characteristic thickness
        volume = float(mesh.volume) if mesh.is_watertight else abs(float(mesh.volume))
        surface_area = float(mesh.area)
        estimated_thickness = volume / max(surface_area, 0.001) * 6  # scale factor

        # Clamp to realistic range
        wall_thickness = max(0.3, min(estimated_thickness, 15.0))

        # Simulate features that can't be directly extracted from mesh
        # Use mesh properties as seeds for consistent results
        np.random.seed(int(surface_area * 100) % (2**31))

        draft_angle = round(np.random.uniform(0.5, 8.0), 2)
        corner_radius = round(np.random.uniform(0.1, 5.0), 2)
        undercut_present = 1 if np.random.random() > 0.6 else 0
        wall_uniformity = round(np.random.uniform(0.4, 1.0), 2)

        return {
            "wall_thickness": round(wall_thickness, 2),
            "draft_angle": draft_angle,
            "corner_radius": corner_radius,
            "aspect_ratio": round(aspect_ratio, 2),
            "undercut_present": undercut_present,
            "wall_uniformity": wall_uniformity,
        }

    except Exception as e:
        print(f"[feature_extractor] STL extraction failed: {e}")
        return None


def _simulate_features(filename: str) -> dict:
    """
    Simulate realistic manufacturing features for demo purposes.
    Uses filename hash for reproducibility.
    """
    # Seed based on filename for consistent results per file
    seed = sum(ord(c) for c in filename) % (2**31)
    rng = random.Random(seed)

    return {
        "wall_thickness": round(rng.uniform(0.5, 10.0), 2),
        "draft_angle": round(rng.uniform(0.5, 8.0), 2),
        "corner_radius": round(rng.uniform(0.1, 5.0), 2),
        "aspect_ratio": round(rng.uniform(1.0, 15.0), 2),
        "undercut_present": rng.choice([0, 1]),
        "wall_uniformity": round(rng.uniform(0.3, 1.0), 2),
    }


def get_material_list() -> list:
    """Return list of available materials."""
    return [
        {"value": "aluminum", "label": "Aluminum"},
        {"value": "steel", "label": "Steel"},
        {"value": "titanium", "label": "Titanium"},
        {"value": "plastic_abs", "label": "Plastic (ABS)"},
        {"value": "plastic_nylon", "label": "Plastic (Nylon)"},
        {"value": "copper", "label": "Copper"},
        {"value": "brass", "label": "Brass"},
        {"value": "stainless_steel", "label": "Stainless Steel"},
    ]
