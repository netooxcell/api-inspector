"""Modelo 3: Gradient Boosting (LightGBM) (H/D/A)."""
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

MODEL_NAME = "gradient_boosting"

try:
    from lightgbm import LGBMClassifier
    _HAS_LGBM = True
except ImportError:  # pragma: no cover - fallback documented in README
    from sklearn.ensemble import GradientBoostingClassifier
    _HAS_LGBM = False


def build_model():
    if _HAS_LGBM:
        clf = LGBMClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.05,
            num_leaves=15, min_child_samples=15, random_state=42, verbosity=-1,
        )
    else:
        clf = GradientBoostingClassifier(n_estimators=200, max_depth=3, random_state=42)
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("clf", clf),
    ])
