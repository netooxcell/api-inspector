# MODEL_COMPARISON.md — Comparación de modelos (walk-forward, fuera de muestra)

Evaluado sobre **1781** partidos fuera de muestra (7 folds walk-forward, temporadas 2019-20 a 2026-2027).

| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) | Log Loss | Brier Score | ROC-AUC (ovr) |
|---|---|---|---|---|---|---|---|
| logistic_regression | 0.4436 | 0.4003 | 0.3969 | 0.3891 | 1.1931 | 0.6874 | 0.5715 |
| random_forest | 0.4655 | 0.2949 | 0.3877 | 0.3254 | 1.0550 | 0.6358 | 0.5704 |
| gradient_boosting | 0.4026 | 0.3522 | 0.3601 | 0.3505 | 1.2933 | 0.7398 | 0.5510 |
| poisson | 0.4750 | 0.3052 | 0.4084 | 0.3468 | 1.0429 | 0.6268 | 0.5960 |
| ensemble | 0.4829 | 0.3111 | 0.4067 | 0.3442 | 1.0400 | 0.6251 | 0.5996 |
| ensemble_calibrated | 0.4919 | 0.4829 | 0.4200 | 0.3623 | 1.0275 | 0.6182 | 0.6172 |

## Pesos del ensemble (ajustados minimizando log loss fuera de muestra)
- logistic_regression: 0.0660
- random_forest: 0.2427
- gradient_boosting: 0.0000
- poisson: 0.6913

## Calibración
Brier score ensemble sin calibrar: 0.6251
Brier score ensemble calibrado (isotónica uno-contra-resto): 0.6182
**Se usa calibración isotónica en producción: True** (se activa solo si mejora el Brier score fuera de muestra).

## Mejor modelo por Log Loss (métrica priorizada, ver Regla 6): **ensemble_calibrated** (log loss = 1.0275)