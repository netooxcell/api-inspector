# MODEL_COMPARISON.md — Comparación de modelos (walk-forward, fuera de muestra)

Evaluado sobre **1772** partidos fuera de muestra (7 folds walk-forward, temporadas 2019-20 a 2026-2027).

| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) | Log Loss | Brier Score | ROC-AUC (ovr) |
|---|---|---|---|---|---|---|---|
| logistic_regression | 0.4453 | 0.4022 | 0.3982 | 0.3907 | 1.1915 | 0.6864 | 0.5726 |
| random_forest | 0.4701 | 0.2989 | 0.3917 | 0.3295 | 1.0542 | 0.6352 | 0.5712 |
| gradient_boosting | 0.4035 | 0.3532 | 0.3606 | 0.3514 | 1.2914 | 0.7387 | 0.5520 |
| poisson | 0.4757 | 0.3060 | 0.4082 | 0.3471 | 1.0420 | 0.6261 | 0.5965 |
| ensemble | 0.4831 | 0.3119 | 0.4055 | 0.3434 | 1.0391 | 0.6245 | 0.6006 |
| ensemble_calibrated | 0.4904 | 0.4698 | 0.4177 | 0.3610 | 1.0278 | 0.6182 | 0.6169 |

## Pesos del ensemble (ajustados minimizando log loss fuera de muestra)
- logistic_regression: 0.0698
- random_forest: 0.2404
- gradient_boosting: 0.0000
- poisson: 0.6898

## Calibración
Brier score ensemble sin calibrar: 0.6245
Brier score ensemble calibrado (isotónica uno-contra-resto): 0.6182
**Se usa calibración isotónica en producción: True** (se activa solo si mejora el Brier score fuera de muestra).

## Mejor modelo por Log Loss (métrica priorizada, ver Regla 6): **ensemble_calibrated** (log loss = 1.0278)