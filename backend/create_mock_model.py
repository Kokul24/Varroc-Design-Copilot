"""
create_mock_model.py — Create a demo model.pkl for testing.
This creates a trained RandomForest classifier that predicts manufacturing risk.

Run once before starting the backend:
    python create_mock_model.py
"""

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
import joblib

# Generate synthetic training data
np.random.seed(42)
n_samples = 2000

# Features: wall_thickness, draft_angle, corner_radius, aspect_ratio,
#           undercut_present, wall_uniformity, material_encoded
X = np.column_stack([
    np.random.uniform(0.3, 12.0, n_samples),   # wall_thickness
    np.random.uniform(0.2, 10.0, n_samples),    # draft_angle
    np.random.uniform(0.05, 6.0, n_samples),    # corner_radius
    np.random.uniform(1.0, 20.0, n_samples),    # aspect_ratio
    np.random.choice([0, 1], n_samples),         # undercut_present
    np.random.uniform(0.2, 1.0, n_samples),     # wall_uniformity
    np.random.choice(range(8), n_samples),       # material_encoded
])

# Generate labels based on realistic DFM rules:
# High risk when:
#   - wall_thickness is too low or too high
#   - draft_angle is insufficient
#   - corner_radius is too small
#   - aspect_ratio is too high
#   - undercuts are present
#   - wall_uniformity is poor
risk_score = np.zeros(n_samples)

# Wall thickness contribution
risk_score += np.where(X[:, 0] < 1.0, 0.25, 0)
risk_score += np.where(X[:, 0] > 8.0, 0.1, 0)

# Draft angle contribution
risk_score += np.where(X[:, 1] < 1.5, 0.2, 0)
risk_score += np.where(X[:, 1] < 0.5, 0.15, 0)  # Extra penalty for very low

# Corner radius contribution
risk_score += np.where(X[:, 2] < 0.5, 0.15, 0)

# Aspect ratio contribution
risk_score += np.where(X[:, 3] > 8.0, 0.1, 0)
risk_score += np.where(X[:, 3] > 12.0, 0.1, 0)

# Undercut contribution
risk_score += X[:, 4] * 0.1

# Wall uniformity contribution (lower = worse)
risk_score += np.where(X[:, 5] < 0.6, 0.15, 0)

# Add some noise
risk_score += np.random.normal(0, 0.05, n_samples)

# Convert to binary labels (1 = high risk, probability > 0.4)
y = (risk_score > 0.35).astype(int)

print(f"Dataset: {n_samples} samples")
print(f"Class distribution: {np.bincount(y)}")
print(f"Positive rate: {y.mean():.2%}")

# Train a Gradient Boosting Classifier
model = GradientBoostingClassifier(
    n_estimators=100,
    max_depth=4,
    learning_rate=0.1,
    random_state=42,
)
model.fit(X, y)

# Evaluate
train_accuracy = model.score(X, y)
print(f"Training accuracy: {train_accuracy:.4f}")

# Save model
output_path = "model.pkl"
joblib.dump(model, output_path)
print(f"\n✅ Model saved to {output_path}")
print("You can now start the backend with: uvicorn main:app --reload")
