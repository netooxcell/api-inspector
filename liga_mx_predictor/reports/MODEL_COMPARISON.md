# MODEL_COMPARISON.md — Comparación de modelos (walk-forward, fuera de muestra)

Evaluado sobre **1756** partidos fuera de muestra (7 folds walk-forward, temporadas 2019-20 a 2026-2027).

| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) | Log Loss | Brier Score | ROC-AUC (ovr) |
|---|---|---|---|---|---|---|---|
| logistic_regression | 0.4442 | 0.4015 | 0.3978 | 0.3905 | 1.1936 | 0.6879 | 0.5714 |
| random_forest | 0.4653 | 0.2949 | 0.3857 | 0.3231 | 1.0551 | 0.6359 | 0.5701 |
| gradient_boosting | 0.4038 | 0.3544 | 0.3615 | 0.3527 | 1.2948 | 0.7399 | 0.5504 |
| poisson | 0.4749 | 0.3054 | 0.4078 | 0.3465 | 1.0433 | 0.6269 | 0.5950 |
| ensemble | 0.4858 | 0.3141 | 0.4089 | 0.3466 | 1.0403 | 0.6253 | 0.5991 |
| ensemble_calibrated | 0.4909 | 0.5152 | 0.4179 | 0.3606 | 1.0279 | 0.6185 | 0.6179 |

## Pesos del ensemble (ajustados minimizando log loss fuera de muestra)
- logistic_regression: 0.0661
- random_forest: 0.2507
- gradient_boosting: 0.0000
- poisson: 0.6832

## Calibración
Brier score ensemble sin calibrar: 0.6253
Brier score ensemble calibrado (isotónica uno-contra-resto): 0.6185
**Se usa calibración isotónica en producción: True** (se activa solo si mejora el Brier score fuera de muestra).

## Mejor modelo por Log Loss (métrica priorizada, ver Regla 6): **ensemble_calibrated** (log loss = 1.0279)