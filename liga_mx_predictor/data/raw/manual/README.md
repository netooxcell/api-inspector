# Partidos confirmados manualmente

TheSportsDB (tier gratuito) solo cataloga 5 de los 9 partidos reales de cada
jornada de Liga MX (ver `reports/DATA_SOURCES.md`). Este archivo contiene
los partidos de la Jornada 4 del Apertura 2026-27 que el usuario confirmó
directamente a partir del calendario oficial, y que no aparecían en ninguna
fuente automática disponible.

No son datos inventados por el modelo: son fixtures y, una vez jugados,
resultados (equipo local, equipo visitante, marcador) proporcionados
directamente por el usuario.

| Archivo | Contenido | Estado |
|---|---|---|
| `jornada4_fixtures.csv` | Santos Laguna vs Guadalajara, Tijuana vs Cruz Azul, Necaxa vs León, Pachuca vs Puebla | **Jugados** — resultados reales confirmados por el usuario el 2026-08-21: Santos 0-1 Chivas, Tijuana 2-1 Cruz Azul, Necaxa 1-2 León, Pachuca 2-3 Puebla. Se agregaron al histórico de entrenamiento con `source="manual_user_confirmed"`. |
| `jornada5_fixtures.csv` | Puebla vs Santos Laguna, Cruz Azul vs Atlas, Atlético San Luis vs Pachuca, Pumas UNAM vs Necaxa | **Jugados** — resultados reales confirmados por el usuario el 2026-08-28: Puebla 3-2 Santos, Cruz Azul 0-2 Atlas, San Luis 1-1 Pachuca, Pumas 1-1 Necaxa. Se agregaron al histórico de entrenamiento con `source="manual_user_confirmed"`. |
