# MODEL_COMPARISON.md — Comparación de modelos (walk-forward, fuera de muestra)

Evaluado sobre **1729** partidos fuera de muestra (7 folds walk-forward, temporadas 2019-20 a 2026-2027).

| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) | Log Loss | Brier Score | ROC-AUC (ovr) |
|---|---|---|---|---|---|---|---|
| logistic_regression | 0.4453 | 0.4013 | 0.3986 | 0.3911 | 1.1846 | 0.6868 | 0.5719 |
| random_forest | 0.4673 | 0.2959 | 0.3881 | 0.3258 | 1.0524 | 0.6342 | 0.5722 |
| gradient_boosting | 0.4060 | 0.3562 | 0.3636 | 0.3547 | 1.2969 | 0.7406 | 0.5500 |
| poisson | 0.4766 | 0.3064 | 0.4088 | 0.3475 | 1.0419 | 0.6260 | 0.5961 |
| ensemble | 0.4853 | 0.3127 | 0.4074 | 0.3450 | 1.0385 | 0.6242 | 0.6002 |
| ensemble_calibrated | 0.4905 | 0.5369 | 0.4179 | 0.3569 | 1.0263 | 0.6177 | 0.6167 |

## Pesos del ensemble (ajustados minimizando log loss fuera de muestra)
- logistic_regression: 0.0678
- random_forest: 0.2666
- gradient_boosting: 0.0000
- poisson: 0.6656

## Calibración
Brier score ensemble sin calibrar: 0.6242
Brier score ensemble calibrado (isotónica uno-contra-resto): 0.6177
**Se usa calibración isotónica en producción: True** (se activa solo si mejora el Brier score fuera de muestra).

## Mejor modelo por Log Loss (métrica priorizada, ver Regla 6): **ensemble_calibrated** (log loss = 1.0263)