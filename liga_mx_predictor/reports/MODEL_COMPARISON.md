# MODEL_COMPARISON.md — Comparación de modelos (walk-forward, fuera de muestra)

Evaluado sobre **1738** partidos fuera de muestra (7 folds walk-forward, temporadas 2019-20 a 2026-2027).

| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) | Log Loss | Brier Score | ROC-AUC (ovr) |
|---|---|---|---|---|---|---|---|
| logistic_regression | 0.4407 | 0.3965 | 0.3936 | 0.3858 | 1.1959 | 0.6889 | 0.5702 |
| random_forest | 0.4678 | 0.2973 | 0.3883 | 0.3259 | 1.0547 | 0.6357 | 0.5670 |
| gradient_boosting | 0.4033 | 0.3542 | 0.3613 | 0.3524 | 1.2960 | 0.7408 | 0.5510 |
| poisson | 0.4753 | 0.3055 | 0.4077 | 0.3466 | 1.0428 | 0.6267 | 0.5952 |
| ensemble | 0.4845 | 0.3129 | 0.4066 | 0.3443 | 1.0399 | 0.6252 | 0.5976 |
| ensemble_calibrated | 0.4948 | 0.5731 | 0.4234 | 0.3690 | 1.0277 | 0.6184 | 0.6175 |

## Pesos del ensemble (ajustados minimizando log loss fuera de muestra)
- logistic_regression: 0.0629
- random_forest: 0.2466
- gradient_boosting: 0.0000
- poisson: 0.6905

## Calibración
Brier score ensemble sin calibrar: 0.6252
Brier score ensemble calibrado (isotónica uno-contra-resto): 0.6184
**Se usa calibración isotónica en producción: True** (se activa solo si mejora el Brier score fuera de muestra).

## Mejor modelo por Log Loss (métrica priorizada, ver Regla 6): **ensemble_calibrated** (log loss = 1.0277)