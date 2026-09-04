# DATA_AUDIT.md — Auditoría inicial del proyecto

**Fecha de auditoría:** 2026-08-14
**Repositorio auditado:** `netooxcell/api-inspector`

## 1. Resultado de la auditoría

Se exploró la totalidad del repositorio `api-inspector` antes de escribir cualquier
línea de código del sistema de predicción, tal como exige el flujo de trabajo
solicitado. Hallazgo principal:

> **El repositorio no contiene ninguna base de datos, dataset, notebook, script
> o documentación relacionada con fútbol / Liga MX.**

Este repo es una herramienta completamente distinta: un *API Request Inspector &
Replay Tool*, un proxy de depuración local (FastAPI + React/Vite) para
desarrolladores que necesitan inspeccionar y repetir llamadas HTTP a APIs.

## 2. Inventario completo encontrado

| Categoría | Hallazgo |
|---|---|
| Databases | `backend/db.py` — SQLite, tabla única `requests` (método, URL, headers, body, status, análisis de errores HTTP). **Sin relación con fútbol.** |
| CSV / Excel / JSON | Ninguno presente en el repo original. |
| Notebooks | Ninguno. |
| Modelos ML existentes | Ninguno. |
| APIs propias | `backend/main.py`, `backend/proxy.py`, `backend/analyzer.py` — proxy HTTP genérico, no deportivo. |
| Configuración | `.env.example` (config del proxy: `DATABASE_PATH`, `UPSTREAM_BASE_URL`, host/puerto). |
| Documentación | `README.md` del inspector de APIs; capturas de pantalla en `docs/screenshots/`. |
| Frontend | React + Vite + TypeScript, UI del inspector de requests. |

## 3. Verificación de otras fuentes propias del usuario

Antes de asumir que no existía ninguna base propia, se verificó:

1. Los 4 repositorios de GitHub accesibles para esta cuenta
   (`uber-didi-comparador`, `api-inspector`, `ssh-cluster-tester`,
   `warehouse-scan-monitor`) — ninguno contiene datos de Liga MX.
2. Se confirmó con el usuario que la base de datos mencionada en la solicitud
   original **no existe** en ninguno de estos repositorios ni fue provista
   como archivo/enlace.

**Conclusión:** no existe una "database existente de Liga MX" que auditar. El
sistema se construye **desde cero**, con datos 100% provenientes de fuentes
externas públicas, documentadas en `DATA_SOURCES.md`.

## 4. Variables disponibles / periodo histórico / equipos / etc.

No aplica al repositorio original (no había datos). Este análisis se traslada
al dataset combinado una vez descargado — ver la sección de calidad de datos
que se genera dinámicamente por `scripts/clean_data.py` (reporte de nulos,
duplicados, rangos de fecha, lista de equipos y de nombres normalizados) y que
se resume al final de este documento tras la primera ejecución del pipeline.

## 5. Riesgos de data leakage identificados de antemano

Aun sin datos previos, se documentan aquí los riesgos que el pipeline debe
evitar activamente (ver `scripts/feature_engineering.py`):

* Usar el resultado del partido como insumo de sus propias features (evidente,
  pero fácil de introducir por accidente al hacer merges por `season`).
* Calcular promedios de temporada completa (incluye partidos futuros al
  partido que se está prediciendo) en lugar de promedios *hasta la fecha*
  (expanding/rolling windows con corte estricto en la fecha del partido).
- Usar la tabla de posiciones final de temporada como feature de partidos
  tempranos de esa misma temporada.
* Mezclar nombres de equipo no normalizados entre fuentes (p. ej. "CF América"
  vs "América" vs "Club América") lo que rompe el cálculo de rolling
  stats/ELO/H2H al tratarlos como entidades distintas.
* Usar el resultado de ida al predecir la vuelta en series de eliminación
  directa (ligas cortas Liga MX: Play-in/Liguilla) sin marcar explícitamente
  qué partidos son de fase regular vs liguilla.

## 6. Nota de alcance

Dado que no había base de datos propia, este documento cumple la función de
"auditoría del proyecto" (paso 1) documentando la ausencia de datos internos y
sirviendo de punto de partida transparente y verificable para el resto del
pipeline, que se basa enteramente en las fuentes descritas en
`DATA_SOURCES.md`.
