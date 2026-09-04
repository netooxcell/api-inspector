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
| `jornada6_fixtures.csv` | América vs Puebla, Santos Laguna vs Tigres UANL, Toluca vs FC Juárez, Monterrey vs Atlético San Luis | **Jugados** — resultados verificados el 2026-09-04 vía búsqueda web (Excélsior y contramuro.com, dos fuentes independientes coincidentes, no vía API): América 2-0 Puebla, Santos 0-0 Tigres, Toluca 4-0 Juárez, Monterrey 1-3 San Luis. Se agregaron al histórico con `source="manual_user_confirmed"`. |
| `jornada7_fixtures.csv` | América vs Tijuana, Atlas vs Atlante, Pumas UNAM vs León, Cruz Azul vs Santos Laguna | **Próximos** — fixtures confirmados por el usuario el 2026-09-04, no jugados aún. |
