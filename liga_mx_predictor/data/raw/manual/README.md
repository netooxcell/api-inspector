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
| `jornada7_fixtures.csv` | Pumas UNAM vs León, Puebla vs Toluca, América vs Tijuana, Querétaro vs Monterrey | **Mixto** — Atlas vs Atlante y Cruz Azul vs Santos (originalmente en este archivo) ya los cubre TheSportsDB automáticamente, se removieron de aquí para no duplicar. Los 4 restantes se pospusieron (América, Monterrey, Toluca y León jugaban semifinal/final de Leagues Cup) — verificado vía búsqueda web (mediotiempo.com, elimparcial.com, olympics.com) el 2026-09-11: **Pumas 3-1 León jugado el 2026-09-10** (verificado en infobae.com y zolonoticias.com), y las reprogramaciones confirmadas: Puebla vs Toluca → 2026-09-15, América vs Tijuana → 2026-10-28, Querétaro vs Monterrey → 2026-11-14 (estos 3 aún no se juegan, se guardan como fixtures futuros con su fecha real, no como "próxima jornada" inmediata). **Actualización 2026-09-18:** Puebla vs Toluca ya se jugó (0-1, autogol al 69', verificado en vavel.com y estamosalaire.com); América vs Tijuana y Querétaro vs Monterrey siguen pendientes. |
| `jornada8_fixtures.csv` | Monterrey vs Tigres UANL, Santos Laguna vs FC Juárez, Guadalajara vs Pumas UNAM, León vs Atlético San Luis | **Jugados** — resultados verificados el 2026-09-18 vía búsqueda web (foxsports.mx, rpp.pe, latinus.us, informador.mx, municipiosur.com, fcjuarez.com — múltiples fuentes independientes coincidentes): Monterrey 0-0 Tigres, Santos 2-1 Juárez, Chivas 3-0 Pumas, León 2-0 San Luis. |
| `jornada9_fixtures.csv` | América vs Guadalajara, Pachuca vs Tijuana, Santos Laguna vs Toluca, Querétaro vs León | **Jugados** — resultados verificados el 2026-09-24 vía búsqueda web (si.com, informador.mx, contramuro.com, news.jointly.mx): América 2-2 Chivas, Pachuca 2-2 Tijuana, Santos 3-2 Toluca, Querétaro 1-1 León. **Corrección**: el archivo original tenía Toluca como local por error de captura; el partido real fue Santos Laguna (local) vs Toluca (visita) — corregido antes de entrenar. |
| `jornada10_fixtures.csv` | Santos Laguna vs Pachuca, Pumas UNAM vs Atlético San Luis, León vs FC Juárez, Necaxa vs América | **Próximos** — fixtures confirmados por el usuario el 2026-09-24, no jugados aún. |
