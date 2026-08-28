# MODEL_ERROR_ANALYSIS.md — Análisis de errores (ensemble, walk-forward)

Basado en 1747 partidos evaluados fuera de muestra.

## 1. Peores predicciones individuales (mayor log loss)
| Fecha | Local | Visitante | Resultado real | P(H)/P(D)/P(A) ensemble | Log loss |
|---|---|---|---|---|---|
| 2019-11-02 | América | Santos Laguna | A (1-2) | 0.60 / 0.27 / 0.14 | 2.001 |
| 2021-07-26 | Cruz Azul | Mazatlán FC | A (0-2) | 0.63 / 0.23 / 0.14 | 1.952 |
| 2024-08-24 | América | Puebla | A (0-1) | 0.63 / 0.23 / 0.14 | 1.952 |
| 2023-06-30 | América | FC Juárez | A (1-2) | 0.63 / 0.23 / 0.14 | 1.952 |
| 2023-05-13 | América | Atlético San Luis | A (1-2) | 0.63 / 0.23 / 0.14 | 1.952 |
| 2021-02-15 | Pachuca | Atlas | A (0-1) | 0.67 / 0.18 / 0.15 | 1.887 |
| 2019-09-24 | Tigres UANL | Puebla | A (0-1) | 0.67 / 0.18 / 0.15 | 1.887 |
| 2021-09-18 | León | FC Juárez | A (0-1) | 0.67 / 0.18 / 0.15 | 1.887 |
| 2023-12-09 | América | Atlético San Luis | A (0-2) | 0.67 / 0.18 / 0.15 | 1.887 |
| 2019-08-03 | Pachuca | Monarcas Morelia | A (1-2) | 0.67 / 0.18 / 0.15 | 1.887 |
| 2019-07-21 | Toluca | Querétaro | A (0-2) | 0.67 / 0.18 / 0.15 | 1.887 |
| 2020-01-11 | Cruz Azul | Atlas | A (1-2) | 0.67 / 0.18 / 0.15 | 1.887 |
| 2022-02-26 | Monterrey | Atlético San Luis | A (0-2) | 0.67 / 0.18 / 0.15 | 1.887 |
| 2019-10-19 | Cruz Azul | Monarcas Morelia | A (2-3) | 0.67 / 0.18 / 0.15 | 1.887 |
| 2022-04-24 | Cruz Azul | Atlético San Luis | A (0-1) | 0.67 / 0.18 / 0.15 | 1.887 |

## 2. Errores sistemáticos por equipo
Tasa de acierto del modelo en partidos de cada equipo (como local o visitante), solo equipos con >= 20 partidos evaluados:
| Equipo | Partidos evaluados | Accuracy | Log loss promedio |
|---|---|---|---|
| Monarcas Morelia | 32 | 0.500 | 1.102 |
| Atlas | 192 | 0.443 | 1.076 |
| Toluca | 191 | 0.424 | 1.074 |
| Cruz Azul | 200 | 0.460 | 1.064 |
| Pachuca | 199 | 0.472 | 1.063 |
| Guadalajara | 199 | 0.457 | 1.057 |
| Puebla | 197 | 0.452 | 1.056 |
| Pumas UNAM | 196 | 0.490 | 1.036 |
| Querétaro | 179 | 0.486 | 1.036 |
| Necaxa | 185 | 0.492 | 1.034 |

(tabla completa ordenada de peor a mejor; se muestran los 10 equipos con mayor error promedio)

## 3. Empates: el punto débil típico de los modelos 1X2
De 465 empates reales, el modelo predijo 'empate' como resultado más probable en solo el **1.3%** de los casos — consistente con el problema conocido en modelos de fútbol de subestimar empates (la clase 'empate' rara vez es la más probable incluso cuando ocurre). El resto de aciertos en general provienen de partidos H/A.

## 4. Upsets (resultado real con probabilidad predicha < 25%)
Total: 277 de 1747 (15.9%)

| Fecha | Local | Visitante | Resultado | P(resultado real) |
|---|---|---|---|---|
| 2019-11-02 | América | Santos Laguna | A (1-2) | 0.14 |
| 2023-06-30 | América | FC Juárez | A (1-2) | 0.14 |
| 2021-07-26 | Cruz Azul | Mazatlán FC | A (0-2) | 0.14 |
| 2023-05-13 | América | Atlético San Luis | A (1-2) | 0.14 |
| 2024-08-24 | América | Puebla | A (0-1) | 0.14 |
| 2020-02-29 | América | Necaxa | A (0-3) | 0.15 |
| 2020-03-15 | Toluca | Atlas | A (2-3) | 0.15 |
| 2019-07-21 | Toluca | Querétaro | A (0-2) | 0.15 |
| 2021-09-18 | León | FC Juárez | A (0-1) | 0.15 |
| 2019-11-30 | León | Monarcas Morelia | A (1-2) | 0.15 |

## 5. Partidos de alta incertidumbre (diferencia entre 1ra y 2da probabilidad < 0.08)
Total: 178 de 1747 (10.2%). Accuracy del modelo específicamente en estos partidos: 0.382 (vs. 0.491 general) — como se espera, el modelo acierta notablemente menos en los partidos que él mismo señala como inciertos, lo cual valida la métrica de incertidumbre como señal útil y no solo un adorno.

## 6. Limitaciones estructurales que explican parte del error
- **Hueco de datos de ~22 meses** entre el fin de la temporada 2024-25 (footballcsv) y el inicio de la Apertura 2026-27 (TheSportsDB): las features de forma reciente de ese fold de test se calculan sobre partidos muy antiguos para varios equipos.
- Sin datos de tiros, posesión, xG, tarjetas o lesiones (ninguna fuente disponible los provee gratuitamente) — el modelo solo puede razonar sobre goles pasados y Elo, lo que limita el techo de rendimiento frente a modelos que sí usan xG.
- Temporadas de entrenamiento tempranas (2018-19, 2019-20) son pequeñas, por lo que los primeros folds del walk-forward entrenan con relativamente poca información.