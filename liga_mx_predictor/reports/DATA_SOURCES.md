# DATA_SOURCES.md — Fuentes externas de datos

Todas las fuentes listadas fueron verificadas manualmente (petición HTTP real,
inspección del contenido crudo) antes de escribir el script de descarga. No se
copió ningún dato a mano: todo se obtiene vía `scripts/download_data.py`.

---

## Fuente 1: footballcsv/mexico (GitHub)

| Campo | Detalle |
|---|---|
| **Nombre** | `footballcsv/mexico` — parte del proyecto `footballcsv` (caché de datos de worldfootball.net / weltfussball.de en formato CSV) |
| **URL** | https://github.com/footballcsv/mexico |
| **Endpoint real usado** | `https://raw.githubusercontent.com/footballcsv/mexico/master/{temporada}/mx.1.csv` |
| **Tipo de datos** | Resultados históricos partido a partido de la primera división de México (Liga MX) |
| **Licencia** | CC0-1.0 (dominio público) |
| **Periodo cubierto (verificado)** | Temporadas **2018-19 a 2024-25** (7 temporadas). Se intentaron las 25 temporadas desde 2000-01; **las temporadas 2000-01 a 2017-18 no tienen archivo `mx.1.csv` en este repositorio** (verificado: HTTP 404 en las 18 temporadas, y confirmado por inspección directa de la carpeta `2015-16/`, que no incluye ningún archivo `mx.*`). No se debe asumir cobertura anterior a 2018-19 de esta fuente. |
| **Variables** | `Stage` (Apertura/Clausura/Liguilla), `Round` (jornada), `Date`, `Time`, `Timezone`, `Team 1` (local), `FT` (marcador final), `HT` (marcador al medio tiempo), `Team 2` (visitante), `ET` (tiempo extra, si aplica), `P` (penales, si aplica), `Comments`, `UTC` |
| **Frecuencia de actualización** | No determinada por el mantenedor; repositorio de caché histórico, no vive. La temporada 2024-25 está incompleta (154 líneas vs. ~343 de una temporada completa), lo que indica que el snapshot se tomó a mitad de temporada. |
| **Limitaciones** | (1) No incluye estadísticas avanzadas: sin tiros, tiros a puerta, posesión, corners, tarjetas, faltas ni xG. (2) No cubre nada anterior a 2018-19. (3) Nombres de equipo inconsistentes entre temporadas y respecto a otras fuentes (ver `team_mapping.csv`), p. ej. "CF América" vs "América", "Deportivo Guadalajara" vs "Gallos Blancos" (Querétaro) vs nombres oficiales actuales. (4) Última temporada incompleta. |
| **Fecha de descarga** | 2026-08-14 |
| **Registros descargados** | 7 archivos CSV, ~2,198 líneas totales (~1,090 partidos aprox. tras remover encabezados y contar solo filas con resultado) |

## Fuente 2: TheSportsDB (API pública)

| Campo | Detalle |
|---|---|
| **Nombre** | TheSportsDB — Free Sports API |
| **URL** | https://www.thesportsdb.com/free_sports_api |
| **Endpoint base** | `https://www.thesportsdb.com/api/v1/json/3/...` (key `3` = key pública de prueba, documentada oficialmente por el proveedor para uso de testing/desarrollo, **no es una credencial inventada ni privada**) |
| **Liga usada** | Liga MX = `idLeague=4350` ("Mexican Primera League" en su catálogo) |
| **Tipo de datos** | Snapshot en vivo: próximo(s) partido(s) programado(s), último(s) resultado(s), tabla de posiciones actual |
| **Endpoints usados** | `eventspastleague.php?id=4350`, `eventsnextleague.php?id=4350`, `lookuptable.php?l=4350&s=2025-2026`, y **`eventsround.php?id=4350&r={1..17}&s=2026-2027`** (round-by-round, ver nota) |
| **Periodo cubierto** | Temporada en curso **Apertura 2026-2027**: resultados reales de las jornadas 1-3 (15 partidos jugados) y calendario de jornadas 4-17 (70 partidos programados, sin resultado). |
| **Variables** | Equipo local/visitante, fecha/hora (UTC y local), marcador, jornada (`intRound`), venue, IDs de equipo/liga, y en la tabla: PJ/PG/PE/PP/GF/GC/DG/Pts |
| **Frecuencia de actualización** | Tiempo real (API en vivo) |
| **Limitaciones (importantes)** | (1) `eventspastleague` y `eventsnextleague` devuelven solo **1 evento cada uno** con la key gratuita — insuficientes por sí solos. **Se descubrió que `eventsround.php` no tiene ese límite de 1 y expone la jornada completa tal como la tiene catalogada el proveedor**, por lo que se adoptó como fuente principal de partidos recientes/próximos (ver `scripts/download_data.py`, función `download_sportsdb`). Aun así, cada jornada devuelta trae **5 partidos, no los 9 reales de una jornada completa de 18 equipos** — el proveedor no tiene catalogados los 4 partidos restantes de cada fecha, no es un límite de paginación (se confirmó pidiendo la misma jornada repetidamente). (2) `lookuptable` devuelve solo **5 de los 18 equipos** y su snapshot correspondía a la tabla final del torneo anterior (Clausura 2026, `dateUpdated: 2026-06-10`), no a la Apertura 2026 en curso — **se excluyó del pipeline de features** por esa razón, se conserva solo como referencia en crudo. (3) El endpoint `lookup_all_teams.php?id=4350` **devuelve datos incorrectos** (equipos de una liga inglesa de categorías inferiores en vez de Liga MX) — **se excluyó del pipeline** tras verificarlo. (4) No requiere autenticación real (key pública documentada), por lo que no aplica ninguna restricción de credenciales. |
| **Uso en el pipeline** | Fuente primaria de partidos **recientes** (Apertura 2026-27, jornadas 1-3) que cierran la brecha temporal desde el final del histórico de footballcsv (2024-25 incompleta) hasta hoy, y fuente primaria de **próximos partidos a predecir** (jornadas 4-17 programadas). `lookuptable` se descarga pero no se usa en features por el desfase de fecha explicado arriba. |
| **Fecha de descarga** | 2026-08-14 |

---

## Fuente 3: partidos confirmados manualmente por el usuario

| Campo | Detalle |
|---|---|
| **Nombre** | Fixtures de Jornada 4 (Apertura 2026-27) confirmados directamente por el usuario |
| **Motivo** | TheSportsDB (tier gratuito) solo catalogó 5 de los 9 partidos reales de la jornada 4 (ver limitación en Fuente 2). El usuario pidió predicción de los 9 partidos reales, incluyendo los 4 faltantes: Santos Laguna vs Guadalajara, Tijuana vs Cruz Azul, Necaxa vs León, Pachuca vs Puebla. |
| **Qué se agregó** | Únicamente equipo local, equipo visitante, jornada y una fecha aproximada (2026-08-16, igual al resto de la jornada — no se confirmó el horario exacto por ninguna fuente automática). **No se agregó ningún resultado**: son fixtures, no marcadores. |
| **Archivo** | `data/raw/manual/jornada4_fixtures.csv`, documentado en `data/raw/manual/README.md` |
| **Fecha de incorporación** | 2026-08-15 |
| **Tratamiento en el pipeline** | Se cargan igual que cualquier otra fuente (`scripts/clean_data.py::load_manual_fixtures`), con `source="manual_user_confirmed"` para que quede trazable en `normalized_events.csv` y en el reporte de calidad. |

---

## Fuentes evaluadas y descartadas

| Fuente | Motivo de exclusión |
|---|---|
| Wikipedia (`2025–26 Liga MX season`) | HTML de las tablas de posiciones/resultados mal formado (atributo `rowspan` inválido), rompe cualquier parser tabular reproducible (`pandas.read_html` falla). Se decidió no scrapear a mano para no violar la regla de "no copiar datos manualmente". |
| Kaggle (`gerardojaimeescareo/ligamx-matches-2016-2022`, otros) | Requieren autenticación (Kaggle API token) para descarga programática. No se inventaron credenciales; se documenta como alternativa futura si el usuario provee una API key de Kaggle. |
| Sportmonks / API-Football / Live-Score API | Requieren API key de pago o registro (trial). Se descartaron por requerir credenciales no provistas. |
| `lookup_all_teams.php` (TheSportsDB) | Devuelve datos de otra liga con la key de prueba — descartado tras verificación (ver arriba). |

## Regla de actualización

Cada ejecución de `scripts/download_data.py` sobrescribe únicamente
`data/raw/{footballcsv,thesportsdb}/*` (los propios archivos crudos "más
recientes"), y registra la fecha de descarga y el resultado de cada intento en
`data/raw/download_manifest.json`. Los datos procesados (`data/processed/`)
nunca se generan a mano; siempre se derivan de `data/raw/` vía
`scripts/clean_data.py` y `scripts/merge_data.py`, preservando así los
crudos originales (Regla 7).
