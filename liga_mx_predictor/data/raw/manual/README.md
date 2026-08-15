# Partidos confirmados manualmente

TheSportsDB (tier gratuito) solo cataloga 5 de los 9 partidos reales de cada
jornada de Liga MX (ver `reports/DATA_SOURCES.md`). Este archivo contiene
los partidos de la Jornada 4 del Apertura 2026-27 que el usuario confirmó
directamente a partir del calendario oficial, y que no aparecían en ninguna
fuente automática disponible.

No son datos inventados por el modelo: son fixtures (equipo local, equipo
visitante, fecha aproximada) proporcionados por el usuario. La fecha exacta
de kickoff no está confirmada por una fuente automática — se usó la misma
fecha que el resto de la jornada (2026-08-16) como aproximación; esto solo
afecta marginalmente a la feature "días de descanso desde el último
partido".

| Archivo | Contenido | Fecha de incorporación |
|---|---|---|
| `jornada4_fixtures.csv` | Santos Laguna vs Guadalajara, Tijuana vs Cruz Azul, Necaxa vs León, Pachuca vs Puebla | 2026-08-15 |
