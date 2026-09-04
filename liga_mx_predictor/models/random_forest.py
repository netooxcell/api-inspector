"""Modelo 2: Random Forest (H/D/A)."""
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

MODEL_NAME = "random_forest"


def build_model():
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("clf", RandomForestClassifier(
            n_estimators=400, max_depth=6, min_samples_leaf=10,
            random_state=42, n_jobs=-1,
        )),
    ])
