# MODEL_COMPARISON.md — Comparación de modelos (walk-forward, fuera de muestra)

Evaluado sobre **1747** partidos fuera de muestra (7 folds walk-forward, temporadas 2019-20 a 2026-2027).

| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) | Log Loss | Brier Score | ROC-AUC (ovr) |
|---|---|---|---|---|---|---|---|
| logistic_regression | 0.4425 | 0.3986 | 0.3954 | 0.3876 | 1.1940 | 0.6879 | 0.5712 |
| random_forest | 0.4677 | 0.2973 | 0.3888 | 0.3267 | 1.0548 | 0.6358 | 0.5697 |
| gradient_boosting | 0.4035 | 0.3543 | 0.3614 | 0.3524 | 1.2944 | 0.7400 | 0.5515 |
| poisson | 0.4757 | 0.3059 | 0.4084 | 0.3471 | 1.0426 | 0.6265 | 0.5952 |
| ensemble | 0.4837 | 0.3122 | 0.4062 | 0.3439 | 1.0397 | 0.6250 | 0.5992 |
| ensemble_calibrated | 0.4911 | 0.4824 | 0.4182 | 0.3611 | 1.0279 | 0.6184 | 0.6188 |

## Pesos del ensemble (ajustados minimizando log loss fuera de muestra)
- logistic_regression: 0.0676
- random_forest: 0.2409
- gradient_boosting: 0.0000
- poisson: 0.6915

## Calibración
Brier score ensemble sin calibrar: 0.6250
Brier score ensemble calibrado (isotónica uno-contra-resto): 0.6184
**Se usa calibración isotónica en producción: True** (se activa solo si mejora el Brier score fuera de muestra).

## Mejor modelo por Log Loss (métrica priorizada, ver Regla 6): **ensemble_calibrated** (log loss = 1.0279)