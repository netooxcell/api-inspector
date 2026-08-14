# DATA_QUALITY_REPORT.md — Reporte de calidad de datos

Generado por `scripts/merge_data.py`. Partidos jugados (con resultado): **2063**.

## Rango de fechas
- Min: 2018-07-20 00:00:00
- Max: 2026-08-03 00:00:00

## Temporadas incluidas
2018-19, 2019-20, 2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2026-2027

## Equipos normalizados (entidades únicas tras mapeo)
Total: 22
- América
- Atlante
- Atlas
- Atlético San Luis
- Cruz Azul
- FC Juárez
- Guadalajara
- León
- Lobos BUAP
- Mazatlán FC
- Monarcas Morelia
- Monterrey
- Necaxa
- Pachuca
- Puebla
- Pumas UNAM
- Querétaro
- Santos Laguna
- Tigres UANL
- Tijuana
- Toluca
- Veracruz

## Valores faltantes por columna (partidos jugados)
- stage: 16
- home_ht_goals: 16
- away_ht_goals: 16

## Duplicados exactos removidos en el merge
0

## Nombres de equipo sin mapeo explícito (usados tal cual aparecen en crudo)
(ninguno — todos los nombres crudos están en team_mapping.csv)

## Filas sin resultado y con fecha pasada excluidas (snapshot obsoleto de footballcsv)
144

## Próximos partidos reales (sin resultado, fecha futura — usados para predicción)
70
- 2026-08-15: Atlante vs Toluca (jornada 4)
- 2026-08-16: Monterrey vs FC Juárez (jornada 4)
- 2026-08-16: Atlas vs Tigres UANL (jornada 4)
- 2026-08-16: Pumas UNAM vs Querétaro (jornada 4)
- 2026-08-16: América vs Atlético San Luis (jornada 4)
- 2026-08-22: FC Juárez vs América (jornada 5)
- 2026-08-22: Guadalajara vs Tijuana (jornada 5)
- 2026-08-22: Tigres UANL vs Atlante (jornada 5)
- 2026-08-22: Querétaro vs Toluca (jornada 5)
- 2026-08-23: Puebla vs Santos Laguna (jornada 5)
- 2026-08-29: Necaxa vs Cruz Azul (jornada 6)
- 2026-08-29: Atlante vs León (jornada 6)
- 2026-08-29: Tijuana vs Pumas UNAM (jornada 6)
- 2026-08-29: Atlas vs Querétaro (jornada 6)
- 2026-08-29: Pachuca vs Guadalajara (jornada 6)
- 2026-09-05: Atlético San Luis vs Guadalajara (jornada 7)
- 2026-09-05: Querétaro vs Monterrey (jornada 7)
- 2026-09-05: FC Juárez vs Pachuca (jornada 7)
- 2026-09-05: Puebla vs Toluca (jornada 7)
- 2026-09-06: Tigres UANL vs Necaxa (jornada 7)
- 2026-09-12: Atlante vs Pachuca (jornada 8)
- 2026-09-12: León vs Atlético San Luis (jornada 8)
- 2026-09-12: Necaxa vs Puebla (jornada 8)
- 2026-09-12: Tijuana vs Querétaro (jornada 8)
- 2026-09-13: Toluca vs Atlas (jornada 8)
- 2026-09-19: Atlético San Luis vs Necaxa (jornada 9)
- 2026-09-19: Atlas vs Pumas UNAM (jornada 9)
- 2026-09-19: Puebla vs Atlante (jornada 9)
- 2026-09-19: FC Juárez vs Tigres UANL (jornada 9)
- 2026-09-20: Monterrey vs Cruz Azul (jornada 9)
- 2026-09-26: Atlante vs Monterrey (jornada 10)
- 2026-09-26: Tijuana vs Atlas (jornada 10)
- 2026-09-26: Guadalajara vs Querétaro (jornada 10)
- 2026-09-27: Santos Laguna vs Pachuca (jornada 10)
- 2026-09-27: Tigres UANL vs Puebla (jornada 10)
- 2026-10-10: Querétaro vs Atlante (jornada 11)
- 2026-10-10: Puebla vs León (jornada 11)
- 2026-10-10: Tigres UANL vs Toluca (jornada 11)
- 2026-10-10: FC Juárez vs Tijuana (jornada 11)
- 2026-10-11: Atlas vs Guadalajara (jornada 11)
- 2026-10-17: Atlante vs Pumas UNAM (jornada 12)
- 2026-10-17: Necaxa vs Atlas (jornada 12)
- 2026-10-17: Guadalajara vs Tigres UANL (jornada 12)
- 2026-10-17: Santos Laguna vs Querétaro (jornada 12)
- 2026-10-17: Tijuana vs Puebla (jornada 12)
- 2026-10-21: FC Juárez vs Atlante (jornada 13)
- 2026-10-21: Atlético San Luis vs Querétaro (jornada 13)
- 2026-10-21: Guadalajara vs Necaxa (jornada 13)
- 2026-10-21: Tigres UANL vs León (jornada 13)
- 2026-10-22: Toluca vs Tijuana (jornada 13)
- 2026-10-24: León vs Toluca (jornada 14)
- 2026-10-24: Necaxa vs FC Juárez (jornada 14)
- 2026-10-24: Atlante vs Atlético San Luis (jornada 14)
- 2026-10-25: Pumas UNAM vs Tigres UANL (jornada 14)
- 2026-10-25: Monterrey vs Guadalajara (jornada 14)
- 2026-10-31: Puebla vs Pumas UNAM (jornada 15)
- 2026-10-31: Pachuca vs Tigres UANL (jornada 15)
- 2026-10-31: FC Juárez vs Querétaro (jornada 15)
- 2026-10-31: Atlético San Luis vs Atlas (jornada 15)
- 2026-11-01: Guadalajara vs Atlante (jornada 15)
- 2026-11-07: Atlético San Luis vs FC Juárez (jornada 16)
- 2026-11-07: Tigres UANL vs Cruz Azul (jornada 16)
- 2026-11-07: Atlante vs Santos Laguna (jornada 16)
- 2026-11-07: Atlas vs Pachuca (jornada 16)
- 2026-11-07: Necaxa vs Tijuana (jornada 16)
- 2026-11-21: Tijuana vs Atlante (jornada 17)
- 2026-11-21: Puebla vs Atlético San Luis (jornada 17)
- 2026-11-21: FC Juárez vs Atlas (jornada 17)
- 2026-11-21: Santos Laguna vs León (jornada 17)
- 2026-11-21: Pachuca vs Toluca (jornada 17)