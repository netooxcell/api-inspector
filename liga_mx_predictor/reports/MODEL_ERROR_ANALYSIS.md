# MODEL_ERROR_ANALYSIS.md — Análisis de errores (ensemble, walk-forward)

Basado en 1762 partidos evaluados fuera de muestra.

## 1. Peores predicciones individuales (mayor log loss)
| Fecha | Local | Visitante | Resultado real | P(H)/P(D)/P(A) ensemble | Log loss |
|---|---|---|---|---|---|
| 2023-05-13 | América | Atlético San Luis | A (1-2) | 0.63 / 0.22 / 0.14 | 1.939 |
| 2026-08-30 | Monterrey | Atlético San Luis | A (1-3) | 0.63 / 0.22 / 0.14 | 1.939 |
| 2021-07-26 | Cruz Azul | Mazatlán FC | A (0-2) | 0.63 / 0.22 / 0.14 | 1.939 |
| 2023-06-30 | América | FC Juárez | A (1-2) | 0.66 / 0.20 / 0.15 | 1.904 |
| 2021-09-18 | León | FC Juárez | A (0-1) | 0.66 / 0.20 / 0.15 | 1.904 |
| 2024-08-24 | América | Puebla | A (0-1) | 0.66 / 0.20 / 0.15 | 1.904 |
| 2021-03-02 | León | Puebla | A (1-2) | 0.67 / 0.18 / 0.15 | 1.882 |
| 2022-02-05 | América | Atlético San Luis | A (2-3) | 0.67 / 0.18 / 0.15 | 1.882 |
| 2021-02-15 | Pachuca | Atlas | A (0-1) | 0.67 / 0.18 / 0.15 | 1.882 |
| 2019-09-24 | Tigres UANL | Puebla | A (0-1) | 0.67 / 0.18 / 0.15 | 1.882 |
| 2022-04-24 | Cruz Azul | Atlético San Luis | A (0-1) | 0.67 / 0.18 / 0.15 | 1.882 |
| 2019-11-30 | León | Monarcas Morelia | A (1-2) | 0.67 / 0.18 / 0.15 | 1.882 |
| 2023-12-09 | América | Atlético San Luis | A (0-2) | 0.67 / 0.18 / 0.15 | 1.882 |
| 2020-02-29 | América | Necaxa | A (0-3) | 0.67 / 0.18 / 0.15 | 1.882 |
| 2020-03-15 | Toluca | Atlas | A (2-3) | 0.67 / 0.18 / 0.15 | 1.882 |

## 2. Errores sistemáticos por equipo
Tasa de acierto del modelo en partidos de cada equipo (como local o visitante), solo equipos con >= 20 partidos evaluados:
| Equipo | Partidos evaluados | Accuracy | Log loss promedio |
|---|---|---|---|
| Monarcas Morelia | 32 | 0.531 | 1.102 |
| Atlas | 194 | 0.428 | 1.085 |
| Toluca | 192 | 0.427 | 1.071 |
| Guadalajara | 201 | 0.453 | 1.060 |
| Cruz Azul | 202 | 0.455 | 1.060 |
| Pachuca | 201 | 0.468 | 1.059 |
| Puebla | 198 | 0.455 | 1.052 |
| Querétaro | 180 | 0.489 | 1.039 |
| Pumas UNAM | 198 | 0.495 | 1.034 |
| Necaxa | 186 | 0.505 | 1.034 |

(tabla completa ordenada de peor a mejor; se muestran los 10 equipos con mayor error promedio)

## 3. Empates: el punto débil típico de los modelos 1X2
De 469 empates reales, el modelo predijo 'empate' como resultado más probable en solo el **0.9%** de los casos — consistente con el problema conocido en modelos de fútbol de subestimar empates (la clase 'empate' rara vez es la más probable incluso cuando ocurre). El resto de aciertos en general provienen de partidos H/A.

## 4. Upsets (resultado real con probabilidad predicha < 25%)
Total: 234 de 1762 (13.3%)

| Fecha | Local | Visitante | Resultado | P(resultado real) |
|---|---|---|---|---|
| 2021-07-26 | Cruz Azul | Mazatlán FC | A (0-2) | 0.14 |
| 2023-05-13 | América | Atlético San Luis | A (1-2) | 0.14 |
| 2026-08-30 | Monterrey | Atlético San Luis | A (1-3) | 0.14 |
| 2021-09-18 | León | FC Juárez | A (0-1) | 0.15 |
| 2024-08-24 | América | Puebla | A (0-1) | 0.15 |
| 2023-06-30 | América | FC Juárez | A (1-2) | 0.15 |
| 2019-07-21 | Toluca | Querétaro | A (0-2) | 0.15 |
| 2019-08-03 | Pachuca | Monarcas Morelia | A (1-2) | 0.15 |
| 2020-03-15 | Toluca | Atlas | A (2-3) | 0.15 |
| 2021-03-02 | León | Puebla | A (1-2) | 0.15 |

## 5. Partidos de alta incertidumbre (diferencia entre 1ra y 2da probabilidad < 0.08)
Total: 145 de 1762 (8.2%). Accuracy del modelo específicamente en estos partidos: 0.379 (vs. 0.490 general) — como se espera, el modelo acierta notablemente menos en los partidos que él mismo señala como inciertos, lo cual valida la métrica de incertidumbre como señal útil y no solo un adorno.

## 6. Limitaciones estructurales que explican parte del error
- **Hueco de datos de ~22 meses** entre el fin de la temporada 2024-25 (footballcsv) y el inicio de la Apertura 2026-27 (TheSportsDB): las features de forma reciente de ese fold de test se calculan sobre partidos muy antiguos para varios equipos.
- Sin datos de tiros, posesión, xG, tarjetas o lesiones (ninguna fuente disponible los provee gratuitamente) — el modelo solo puede razonar sobre goles pasados y Elo, lo que limita el techo de rendimiento frente a modelos que sí usan xG.
- Temporadas de entrenamiento tempranas (2018-19, 2019-20) son pequeñas, por lo que los primeros folds del walk-forward entrenan con relativamente poca información.