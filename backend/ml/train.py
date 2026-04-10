"""
ml/train.py — Training script for the DFM risk prediction model.

Loads the real dataset, preprocesses it, trains an XGBoost model,
evaluates performance, and saves all artifacts needed for inference.

Usage:
    python -m ml.train

Artifacts produced:
    - model.pkl             (trained XGBoost model)
    - feature_columns.pkl   (ordered feature column names)
    - label_encoder.pkl     (material label encoder)
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore", category=UserWarning)

# ============================================================
# Paths
# ============================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "dfm_dataset.csv")
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
FEATURE_COLS_PATH = os.path.join(BASE_DIR, "feature_columns.pkl")
LABEL_ENCODER_PATH = os.path.join(BASE_DIR, "label_encoder.pkl")

# Feature columns expected in the dataset
FEATURE_COLUMNS = [
    "wall_thickness",
    "draft_angle",
    "corner_radius",
    "aspect_ratio",
    "undercut_present",
    "wall_uniformity",
    "material_encoded",
]

# Additional engineered features for interaction handling
INTERACTION_FEATURES = [
    "wall_ar_interaction",        # thin wall × high aspect ratio
    "draft_undercut_interaction", # low draft × undercut
    "wall_uniformity_interaction",# thin wall × poor uniformity
]


def load_dataset(path: str) -> pd.DataFrame:
    """
    Load and validate the DFM dataset.

    Args:
        path: Path to the CSV file

    Returns:
        Loaded DataFrame

    Raises:
        FileNotFoundError: If dataset file is missing
        ValueError: If dataset is empty or corrupted
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Dataset not found at {path}. "
            "Ensure data/dfm_dataset.csv exists."
        )

    try:
        df = pd.read_csv(path)
    except Exception as e:
        raise ValueError(f"Failed to read CSV: {e}")

    if df.empty:
        raise ValueError("Dataset is empty — cannot train model.")

    if len(df) < 10:
        raise ValueError(
            f"Dataset too small ({len(df)} rows). "
            "Need at least 10 rows for meaningful training."
        )

    print(f"[train] Loaded dataset: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"[train] Columns: {list(df.columns)}")
    return df


def preprocess(df: pd.DataFrame) -> tuple:
    """
    Preprocess the raw dataset for model training.

    Steps:
    1. Handle missing values
    2. Encode categorical 'material' column
    3. Engineer interaction features
    4. Determine target variable
    5. Split features and target

    Args:
        df: Raw DataFrame

    Returns:
        Tuple of (X, y, label_encoder, feature_names, is_classification)
    """
    df = df.copy()

    # --- 1. Handle missing values ---
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object"]).columns.tolist()

    # Check for critical missing features
    critical_cols = [
        "wall_thickness", "draft_angle", "corner_radius",
        "aspect_ratio", "undercut_present", "wall_uniformity",
    ]
    existing_critical = [c for c in critical_cols if c in df.columns]

    # Drop rows where ALL critical features are missing
    before_drop = len(df)
    df.dropna(subset=existing_critical, how="all", inplace=True)

    # Impute remaining missing numeric values with median
    for col in numeric_cols:
        if col in df.columns and df[col].isnull().any():
            median_val = df[col].median()
            df[col].fillna(median_val, inplace=True)
            print(f"[train] Imputed {col} missing values with median: {median_val:.4f}")

    # Impute missing categoricals with mode
    for col in cat_cols:
        if col in df.columns and df[col].isnull().any():
            mode_val = df[col].mode()[0]
            df[col].fillna(mode_val, inplace=True)
            print(f"[train] Imputed {col} missing values with mode: {mode_val}")

    dropped = before_drop - len(df)
    if dropped > 0:
        print(f"[train] Dropped {dropped} rows with all critical features missing")

    # --- 2. Encode material column ---
    le = LabelEncoder()
    if "material" in df.columns:
        df["material_encoded"] = le.fit_transform(df["material"].astype(str))
        print(f"[train] Material classes: {dict(zip(le.classes_, le.transform(le.classes_)))}")
    else:
        # If no material column, create dummy encoding
        df["material_encoded"] = 0
        le.classes_ = np.array(["unknown"])
        print("[train] Warning: No 'material' column found, using default encoding")

    # --- 3. Engineer interaction features ---
    # Interaction 1: thin wall × high aspect ratio
    # Values closer to 1.0 indicate worse combined conditions
    min_wall = 1.0
    max_ar = 8.0
    wall_deficit = np.clip((min_wall - df["wall_thickness"]) / min_wall, 0, 1)
    ar_excess = np.clip((df["aspect_ratio"] - max_ar) / max_ar, 0, 1)
    df["wall_ar_interaction"] = wall_deficit * ar_excess

    # Interaction 2: low draft × undercut
    min_draft = 1.5
    draft_deficit = np.clip((min_draft - df["draft_angle"]) / min_draft, 0, 1)
    df["draft_undercut_interaction"] = draft_deficit * df["undercut_present"]

    # Interaction 3: thin wall × poor uniformity
    min_uniform = 0.6
    uniform_deficit = np.clip((min_uniform - df["wall_uniformity"]) / min_uniform, 0, 1)
    df["wall_uniformity_interaction"] = wall_deficit * uniform_deficit

    # --- 4. Determine target variable ---
    # The dataset has both 'risk_score' (continuous) and 'failure' (binary)
    # We'll train a regression model on risk_score for continuous predictions,
    # and use 'failure' as a secondary classification target
    has_risk_score = "risk_score" in df.columns
    has_failure = "failure" in df.columns

    if has_risk_score:
        # Regression on continuous risk_score (0-100)
        target = df["risk_score"].values
        is_classification = False
        print(f"[train] Target: risk_score (regression)")
        print(f"[train] Target stats: mean={target.mean():.2f}, "
              f"std={target.std():.2f}, min={target.min():.2f}, max={target.max():.2f}")
    elif has_failure:
        target = df["failure"].values.astype(int)
        is_classification = True
        print(f"[train] Target: failure (classification)")
        print(f"[train] Class distribution: {np.bincount(target)}")
    else:
        raise ValueError("Dataset must contain either 'risk_score' or 'failure' column")

    # --- 5. Build feature matrix ---
    all_feature_cols = FEATURE_COLUMNS + INTERACTION_FEATURES
    existing_features = [c for c in all_feature_cols if c in df.columns]

    X = df[existing_features].values
    y = target

    print(f"[train] Feature matrix shape: {X.shape}")
    print(f"[train] Features used: {existing_features}")

    return X, y, le, existing_features, is_classification


def train_model(X, y, is_classification: bool):
    """
    Train an XGBoost model with proper train/test split.

    Args:
        X: Feature matrix
        y: Target vector
        is_classification: Whether to use classifier or regressor

    Returns:
        Tuple of (trained_model, metrics_dict)
    """
    # Import xgboost, fall back to sklearn if not available
    try:
        from xgboost import XGBRegressor, XGBClassifier
        use_xgboost = True
        print("[train] Using XGBoost")
    except ImportError:
        from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier
        use_xgboost = False
        print("[train] XGBoost not available, using sklearn GradientBoosting")

    # --- Train/test split (80/20), stratified for classification ---
    stratify = y if is_classification else None

    # For regression, we can bin the target for stratified split
    if not is_classification:
        bins = pd.qcut(y, q=5, labels=False, duplicates="drop")
        stratify = bins

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=stratify
    )
    print(f"[train] Train: {X_train.shape[0]} samples, Test: {X_test.shape[0]} samples")

    # --- Model selection ---
    if is_classification:
        if use_xgboost:
            model = XGBClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                eval_metric="logloss",
                use_label_encoder=False,
            )
        else:
            model = GradientBoostingClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                random_state=42,
            )
    else:
        if use_xgboost:
            model = XGBRegressor(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                eval_metric="rmse",
            )
        else:
            model = GradientBoostingRegressor(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                random_state=42,
            )

    # --- Train ---
    print("[train] Training model...")
    model.fit(X_train, y_train)

    # --- Evaluate ---
    metrics = {}
    y_pred = model.predict(X_test)

    if is_classification:
        accuracy = accuracy_score(y_test, y_pred)
        metrics["accuracy"] = round(accuracy, 4)
        print(f"\n[train] === CLASSIFICATION RESULTS ===")
        print(f"[train] Accuracy: {accuracy:.4f}")
        print(f"\n{classification_report(y_test, y_pred, zero_division=0)}")
    else:
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        metrics["rmse"] = round(rmse, 4)
        metrics["mae"] = round(mae, 4)
        metrics["r2"] = round(r2, 4)
        print(f"\n[train] === REGRESSION RESULTS ===")
        print(f"[train] RMSE:  {rmse:.4f}")
        print(f"[train] MAE:   {mae:.4f}")
        print(f"[train] R²:    {r2:.4f}")

        # Show prediction distribution
        print(f"\n[train] Prediction stats:")
        print(f"  Predicted: mean={y_pred.mean():.2f}, std={y_pred.std():.2f}")
        print(f"  Actual:    mean={y_test.mean():.2f}, std={y_test.std():.2f}")

    return model, metrics


def save_artifacts(model, feature_columns: list, label_encoder):
    """
    Save all model artifacts to disk.

    Saves:
    - model.pkl: Trained model
    - feature_columns.pkl: Ordered feature column names
    - label_encoder.pkl: Material label encoder
    """
    joblib.dump(model, MODEL_PATH)
    print(f"[train] [OK] Model saved to {MODEL_PATH}")

    joblib.dump(feature_columns, FEATURE_COLS_PATH)
    print(f"[train] [OK] Feature columns saved to {FEATURE_COLS_PATH}")

    joblib.dump(label_encoder, LABEL_ENCODER_PATH)
    print(f"[train] [OK] Label encoder saved to {LABEL_ENCODER_PATH}")


def main():
    """Run the full training pipeline."""
    print("=" * 60)
    print("  CADguard ML Training Pipeline")
    print("=" * 60)

    # 1. Load dataset
    df = load_dataset(DATA_PATH)

    # 2. Preprocess
    X, y, label_encoder, feature_names, is_classification = preprocess(df)

    # 3. Train model
    model, metrics = train_model(X, y, is_classification)

    # 4. Save artifacts
    save_artifacts(model, feature_names, label_encoder)

    print("\n" + "=" * 60)
    print("  Training Complete!")
    print(f"  Model type: {'Classification' if is_classification else 'Regression'}")
    print(f"  Metrics: {metrics}")
    print("=" * 60)


if __name__ == "__main__":
    main()
