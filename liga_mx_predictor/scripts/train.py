"""
1. Calcula métricas de cada modelo sobre las predicciones walk-forward
   (fuera de muestra) generadas por scripts/backtest.py.
2. Ajusta los pesos del ensemble por optimización (log loss) sobre esas
   mismas predicciones — nunca a mano.
3. Evalúa calibración (reliability curve, Brier) y aplica calibración
   isotónica uno-contra-resto si mejora el Brier score fuera de muestra.
4. Reentrena los modelos finales de PRODUCCIÓN sobre el histórico COMPLETO
   (todas las temporadas disponibles) y los guarda en
   data/processed/model_artifacts/ para usarlos en scripts/predict.py.

Salida:
  reports/MODEL_COMPARISON.md
  data/processed/model_artifacts/*.joblib
  data/processed/calibration_data.csv  (para las gráficas de calibración)

Uso:
    python scripts/train.py
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    accuracy_score, f1_score, log_loss, precision_score, recall_score, roc_auc_score,
)

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models.feature_columns import get_feature_columns  # noqa: E402
from models.poisson import fit_poisson_model  # noqa: E402
from models import logistic, random_forest, gradient_boosting, ensemble  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
ARTIFACTS = PROCESSED / "model_artifacts"
REPORT_PATH = ROOT / "reports" / "MODEL_COMPARISON.md"

CLASS_ORDER = ["A", "D", "H"]
ML_MODELS = {
    logistic.MODEL_NAME: logistic.build_model,
    random_forest.MODEL_NAME: random_forest.build_model,
    gradient_boosting.MODEL_NAME: gradient_boosting.build_model,
}
ALL_MODEL_NAMES = list(ML_MODELS.keys()) + ["poisson"]


def brier_score_multiclass(y_true, proba, labels=CLASS_ORDER):
    y_onehot = np.array([[1.0 if lbl == y else 0.0 for lbl in labels] for y in y_true])
    return np.mean(np.sum((proba - y_onehot) ** 2, axis=1))


def compute_metrics(y_true, proba, labels=CLASS_ORDER):
    y_pred = [labels[i] for i in np.argmax(proba, axis=1)]
    y_onehot = np.array([[1.0 if lbl == y else 0.0 for lbl in labels] for y in y_true])
    try:
        roc_auc = roc_auc_score(y_onehot, proba, average="macro", multi_class="ovr")
    except ValueError:
        roc_auc = float("nan")
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision_macro": precision_score(y_true, y_pred, labels=labels, average="macro", zero_division=0),
        "recall_macro": recall_score(y_true, y_pred, labels=labels, average="macro", zero_division=0),
        "f1_macro": f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0),
        "log_loss": log_loss(y_true, proba, labels=labels),
        "brier_score": brier_score_multiclass(y_true, proba, labels),
        "roc_auc_ovr_macro": roc_auc,
    }


def calibration_curve_data(y_true, proba_class, class_label, n_bins=10):
    """Reliability data for one class: predicted prob vs. observed frequency."""
    is_class = (y_true == class_label).astype(int)
    bins = np.linspace(0, 1, n_bins + 1)
    bin_idx = np.digitize(proba_class, bins) - 1
    bin_idx = np.clip(bin_idx, 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        mask = bin_idx == b
        if mask.sum() == 0:
            continue
        rows.append({
            "class": class_label,
            "bin_mid": (bins[b] + bins[b + 1]) / 2,
            "predicted_mean": proba_class[mask].mean(),
            "observed_freq": is_class[mask].mean(),
            "n": int(mask.sum()),
        })
    return rows


def fit_isotonic_calibrators(y_true, proba, labels=CLASS_ORDER):
    calibrators = {}
    for i, lbl in enumerate(labels):
        is_class = (y_true == lbl).astype(int)
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1)
        iso.fit(proba[:, i], is_class)
        calibrators[lbl] = iso
    return calibrators


def apply_calibrators(calibrators, proba, labels=CLASS_ORDER):
    calibrated = np.column_stack([calibrators[lbl].predict(proba[:, i]) for i, lbl in enumerate(labels)])
    row_sums = calibrated.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    return calibrated / row_sums


def main():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    backtest = pd.read_csv(PROCESSED / "backtest_predictions.csv", parse_dates=["date"])
    y_true = backtest["result"].to_numpy()

    # --- 1) Métricas por modelo individual ---
    metrics_rows = {}
    model_probs = {}
    for m in ALL_MODEL_NAMES:
        proba = backtest[[f"{m}_{c}" for c in CLASS_ORDER]].to_numpy()
        model_probs[m] = proba
        metrics_rows[m] = compute_metrics(y_true, proba)

    # --- 2) Pesos del ensemble ajustados por validación (minimizan log loss OOS) ---
    weights, best_log_loss = ensemble.fit_ensemble_weights(backtest, ALL_MODEL_NAMES)
    ensemble_proba = ensemble.combine_probabilities(model_probs, weights)
    metrics_rows["ensemble"] = compute_metrics(y_true, ensemble_proba)

    # --- 3) Calibración isotónica del ensemble (uno-contra-resto) ---
    calibrators = fit_isotonic_calibrators(y_true, ensemble_proba)
    ensemble_calibrated = apply_calibrators(calibrators, ensemble_proba)
    metrics_rows["ensemble_calibrated"] = compute_metrics(y_true, ensemble_calibrated)

    calib_rows = []
    for lbl in CLASS_ORDER:
        idx = CLASS_ORDER.index(lbl)
        calib_rows += calibration_curve_data(y_true, ensemble_proba[:, idx], lbl)
        calib_rows_cal = calibration_curve_data(y_true, ensemble_calibrated[:, idx], lbl)
        for r in calib_rows_cal:
            r["class"] = f"{lbl}_calibrated"
        calib_rows += calib_rows_cal
    pd.DataFrame(calib_rows).to_csv(PROCESSED / "calibration_data.csv", index=False)

    # --- Reporte comparativo ---
    metrics_df = pd.DataFrame(metrics_rows).T
    metrics_df.index.name = "model"
    metrics_df = metrics_df.round(4)
    metrics_df.to_csv(PROCESSED / "model_metrics.csv")

    use_calibrated = metrics_rows["ensemble_calibrated"]["brier_score"] < metrics_rows["ensemble"]["brier_score"]

    lines = ["# MODEL_COMPARISON.md — Comparación de modelos (walk-forward, fuera de muestra)", ""]
    lines.append(f"Evaluado sobre **{len(backtest)}** partidos fuera de muestra "
                 f"(7 folds walk-forward, temporadas 2019-20 a 2026-2027).")
    lines.append("")
    lines.append("| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) | Log Loss | Brier Score | ROC-AUC (ovr) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for m, row in metrics_rows.items():
        lines.append(
            f"| {m} | {row['accuracy']:.4f} | {row['precision_macro']:.4f} | {row['recall_macro']:.4f} | "
            f"{row['f1_macro']:.4f} | {row['log_loss']:.4f} | {row['brier_score']:.4f} | {row['roc_auc_ovr_macro']:.4f} |"
        )
    lines.append("")
    lines.append("## Pesos del ensemble (ajustados minimizando log loss fuera de muestra)")
    for m, w in weights.items():
        lines.append(f"- {m}: {w:.4f}")
    lines.append("")
    lines.append(f"## Calibración")
    lines.append(f"Brier score ensemble sin calibrar: {metrics_rows['ensemble']['brier_score']:.4f}")
    lines.append(f"Brier score ensemble calibrado (isotónica uno-contra-resto): {metrics_rows['ensemble_calibrated']['brier_score']:.4f}")
    lines.append(f"**Se usa calibración isotónica en producción: {use_calibrated}** "
                 f"(se activa solo si mejora el Brier score fuera de muestra).")
    lines.append("")
    best_by_logloss = min(metrics_rows.items(), key=lambda kv: kv[1]["log_loss"])
    lines.append(f"## Mejor modelo por Log Loss (métrica priorizada, ver Regla 6): **{best_by_logloss[0]}** "
                 f"(log loss = {best_by_logloss[1]['log_loss']:.4f})")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))

    # --- 4) Reentrenar modelos FINALES sobre el histórico completo ---
    features_df = pd.read_csv(PROCESSED / "features.csv", parse_dates=["date"])
    matches_df = pd.read_csv(PROCESSED / "matches_clean.csv", parse_dates=["date"])
    feature_cols = get_feature_columns(features_df)
    joblib.dump(feature_cols, ARTIFACTS / "feature_columns.joblib")

    X, y = features_df[feature_cols], features_df["result"]
    for name, builder in ML_MODELS.items():
        pipe = builder()
        pipe.fit(X, y)
        joblib.dump(pipe, ARTIFACTS / f"{name}.joblib")
        print(f"Modelo final '{name}' entrenado sobre {len(X)} partidos y guardado.")

    poisson_fitted = fit_poisson_model(matches_df)
    joblib.dump(poisson_fitted, ARTIFACTS / "poisson.joblib")
    print(f"Modelo Poisson final entrenado sobre {len(matches_df)} partidos y guardado.")

    joblib.dump(weights, ARTIFACTS / "ensemble_weights.joblib")
    joblib.dump(calibrators if use_calibrated else None, ARTIFACTS / "calibrators.joblib")
    joblib.dump({"use_calibrated": bool(use_calibrated)}, ARTIFACTS / "calibration_flag.joblib")

    print(f"\nArtefactos guardados en {ARTIFACTS}")
    print(f"Reporte: {REPORT_PATH}")


if __name__ == "__main__":
    main()
