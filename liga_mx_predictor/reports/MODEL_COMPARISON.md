# MODEL_COMPARISON.md — Comparación de modelos (walk-forward, fuera de muestra)

Evaluado sobre **1762** partidos fuera de muestra (7 folds walk-forward, temporadas 2019-20 a 2026-2027).

| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) | Log Loss | Brier Score | ROC-AUC (ovr) |
|---|---|---|---|---|---|---|---|
| logistic_regression | 0.4461 | 0.4035 | 0.3998 | 0.3923 | 1.1925 | 0.6870 | 0.5720 |
| random_forest | 0.4694 | 0.6321 | 0.3904 | 0.3288 | 1.0538 | 0.6350 | 0.5731 |
| gradient_boosting | 0.4047 | 0.3550 | 0.3623 | 0.3533 | 1.2927 | 0.7388 | 0.5514 |
| poisson | 0.4762 | 0.3062 | 0.4091 | 0.3476 | 1.0426 | 0.6265 | 0.5955 |
| ensemble | 0.4852 | 0.3136 | 0.4080 | 0.3456 | 1.0395 | 0.6248 | 0.6000 |
| ensemble_calibrated | 0.4904 | 0.4636 | 0.4187 | 0.3598 | 1.0275 | 0.6181 | 0.6167 |

## Pesos del ensemble (ajustados minimizando log loss fuera de muestra)
- logistic_regression: 0.0664
- random_forest: 0.2585
- gradient_boosting: 0.0000
- poisson: 0.6751

## Calibración
Brier score ensemble sin calibrar: 0.6248
Brier score ensemble calibrado (isotónica uno-contra-resto): 0.6181
**Se usa calibración isotónica en producción: True** (se activa solo si mejora el Brier score fuera de muestra).

## Mejor modelo por Log Loss (métrica priorizada, ver Regla 6): **ensemble_calibrated** (log loss = 1.0275)