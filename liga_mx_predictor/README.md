# Liga MX Predictor

Sistema estadístico reproducible de predicción probabilística de partidos de
Liga MX: adquisición de datos → limpieza → integración → feature engineering
→ modelado (ELO, Poisson, Regresión Logística, Random Forest, Gradient
Boosting) → ensemble → validación temporal (walk-forward) → calibración →
simulación Monte Carlo → predicción de la próxima jornada.

> **Nota de contexto:** este subproyecto vive dentro del repositorio
> `api-inspector` (una herramienta de inspección de APIs sin relación con
> fútbol). No existía ninguna base de datos de Liga MX previa en este
> repositorio ni en ningún otro repositorio accesible del usuario — ver
> `reports/DATA_AUDIT.md`. Todo el histórico usado aquí proviene de fuentes
> públicas externas, documentadas en `reports/DATA_SOURCES.md`.

## Objetivo

Generar probabilidades bien calibradas (no solo "quién gana") para los
próximos partidos de Liga MX, con evidencia de que el modelo funciona
mediante backtesting temporal — no solo una predicción que "suene
convincente".

## Fuentes de datos

| Fuente | Qué aporta | Periodo |
|---|---|---|
| [footballcsv/mexico](https://github.com/footballcsv/mexico) (CC0) | Resultados históricos partido a partido | 2018-19 a 2024-25 (parcial) |
| [TheSportsDB](https://www.thesportsdb.com/free_sports_api) (key pública de prueba) | Resultados y calendario de la temporada en curso | Apertura 2026-2027 |

Detalle completo, limitaciones de cada fuente y fuentes descartadas (y por
qué) en `reports/DATA_SOURCES.md`. **Hueco de datos conocido:** no existe
ninguna fuente gratuita disponible para la temporada 2025-26 completa; el
histórico salta de septiembre de 2024 a julio de 2026. Esto se documenta y
se tiene en cuenta explícitamente en el backtesting y el análisis de errores
— no se rellena con datos inventados.

## Estructura del proyecto

```
liga_mx_predictor/
├── data/
│   ├── raw/            # descargas crudas, nunca se editan a mano
│   ├── external/        # team_mapping.csv (normalización de nombres)
│   ├── processed/       # datos limpios, features, artefactos de modelos
│   └── predictions/     # (reservado; las predicciones finales están en /predictions)
├── models/               # lógica de cada modelo (ELO, Poisson, ML, ensemble)
├── scripts/              # pipeline ejecutable paso a paso
├── reports/
│   ├── figures/          # gráficas generadas
│   ├── DATA_AUDIT.md
│   ├── DATA_SOURCES.md
│   ├── DATA_QUALITY_REPORT.md
│   ├── MODEL_COMPARISON.md
│   └── MODEL_ERROR_ANALYSIS.md
└── predictions/
    ├── current_predictions.csv
    └── current_predictions.md
```

## Cómo ejecutar el pipeline completo

Requiere Python 3.11+ y las dependencias: `pandas numpy scikit-learn scipy
statsmodels lightgbm matplotlib joblib requests`.

```bash
cd liga_mx_predictor

python scripts/download_data.py       # 1. descarga cruda (reproducible)
python scripts/clean_data.py          # 2. normaliza cada fuente
python scripts/merge_data.py          # 3. combina, dedupe, separa jugados/próximos
python scripts/feature_engineering.py # 4. ELO + H2H + forma + splits local/visitante
python scripts/backtest.py            # 5. validación walk-forward (todas las temporadas)
python scripts/train.py               # 6. métricas + pesos del ensemble + calibración + modelos finales
python scripts/analyze_errors.py      # 7. reports/MODEL_ERROR_ANALYSIS.md
python scripts/predict.py             # 8. predicciones/current_predictions.{csv,md}
python scripts/visualize.py           # 9. reports/figures/*.png
```

Cada script es idempotente y puede re-ejecutarse de forma independiente
mientras existan los artefactos de los pasos anteriores.

### Actualizar datos y predicciones

Repite la secuencia completa. `download_data.py` sobrescribe únicamente
`data/raw/` (nunca los datos procesados a mano) y registra la fecha de
descarga en `data/raw/download_manifest.json`.

## Metodología (resumen)

- **Anti-leakage:** toda feature de un partido usa exclusivamente
  información estrictamente anterior a su fecha (`shift(1)` antes de
  cualquier rolling/expanding). Ver el docstring de
  `scripts/feature_engineering.py`.
- **ELO:** variante de World Football Elo Ratings, con ventaja de local
  (+80 pts) y multiplicador por margen de victoria (`models/elo.py`).
- **Poisson:** modelo de Maher (ataque/defensa por equipo vía GLM Poisson)
  con corrección de Dixon-Coles para marcadores bajos (`models/poisson.py`).
- **ML:** Regresión Logística, Random Forest y Gradient Boosting (LightGBM)
  sobre ~70 features (forma, ELO, H2H, splits local/visitante, descanso).
- **Ensemble:** combinación convexa de los 4 modelos con pesos ajustados
  minimizando log loss **fuera de muestra** (optimización SLSQP), nunca
  asignados a mano — ver `models/ensemble.py`.
- **Validación:** walk-forward por temporada (expanding window), nunca
  split aleatorio. 7 folds, 1,729 partidos evaluados fuera de muestra.
- **Calibración:** isotónica uno-contra-resto, activada solo si mejora el
  Brier score fuera de muestra (en esta corrida sí mejora).
- **Monte Carlo:** 10,000 simulaciones por partido, muestreando directamente
  de la matriz de marcadores del modelo Poisson (con corrección Dixon-Coles).

## Cómo interpretar las probabilidades

Las probabilidades reportadas son estimaciones de un modelo estadístico con
incertidumbre real — **no certezas**. En el backtest, el modelo alcanza
~49% de accuracy y un log loss de ~1.03 (el azar puro sobre 3 clases da
log loss ≈ 1.10), lo cual es una mejora modesta y honesta, consistente con
lo difícil que es predecir fútbol sin datos de xG/tiros. Ver
`reports/MODEL_COMPARISON.md` para la tabla completa y
`reports/MODEL_ERROR_ANALYSIS.md` para los patrones de error conocidos
(en particular: el modelo casi nunca predice "empate" como resultado más
probable, aunque sí lo asigna con probabilidad razonable).

## Limitaciones

1. Sin datos de tiros, tiros a puerta, posesión, corners, tarjetas, faltas
   ni xG — ninguna fuente gratuita disponible los provee; las features de
   ataque/defensa se basan solo en goles.
2. Sin datos de lesiones/suspensiones — no se inventan.
3. Hueco de ~22 meses sin datos (temporada 2025-26 completa).
4. TheSportsDB en su tier gratuito solo expone 5 de los 9 partidos reales
   de cada jornada — la "próxima jornada" predicha puede estar incompleta
   frente al calendario real.
5. El histórico útil empieza en 2018-19 (7 temporadas), no hay datos de
   footballcsv anteriores a esa fecha para Liga MX.

## Reglas seguidas (ver enunciado original)

No se inventaron datos ni fuentes; no se usó información posterior al
kickoff en ningún feature; no se usó split aleatorio para la validación
principal; el modelo no se eligió solo por accuracy sino priorizando log
loss/Brier; se conservaron los datasets crudos originales; toda descarga es
reproducible vía script; se registran las fechas de descarga; y cuando una
fuente falló o dio datos incorrectos (`lookup_all_teams.php`, tabla de
posiciones desactualizada) se documentó explícitamente en vez de ocultarlo.
