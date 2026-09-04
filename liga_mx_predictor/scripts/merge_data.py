"""
Combina los eventos normalizados de todas las fuentes en el dataset final.

Entrada:  data/processed/normalized_events.csv  (salida de scripts/clean_data.py)
Salida:   data/processed/matches_clean.csv      (partidos jugados, usados para
                                                   entrenar/backtest)
          data/processed/fixtures_upcoming.csv  (próximos partidos reales, sin
                                                   resultado, usados para predecir)
          reports/DATA_QUALITY_REPORT.md        (nulos, duplicados, rangos,
                                                   equipos, partidos excluidos)

Uso:
    python scripts/clean_data.py && python scripts/merge_data.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
TEAM_MAPPING_PATH = ROOT / "data" / "external" / "team_mapping.csv"
QUALITY_REPORT_PATH = ROOT / "reports" / "DATA_QUALITY_REPORT.md"


def build_quality_report(played_df, unmapped_teams, dupes, fixtures_df, stale_unplayed_n):
    lines = ["# DATA_QUALITY_REPORT.md — Reporte de calidad de datos", ""]
    lines.append(f"Generado por `scripts/merge_data.py`. Partidos jugados (con resultado): **{len(played_df)}**.")
    lines.append("")
    lines.append("## Rango de fechas")
    lines.append(f"- Min: {played_df['date'].min()}")
    lines.append(f"- Max: {played_df['date'].max()}")
    lines.append("")
    lines.append("## Temporadas incluidas")
    lines.append(", ".join(sorted(played_df['season'].dropna().astype(str).unique())))
    lines.append("")
    lines.append("## Equipos normalizados (entidades únicas tras mapeo)")
    teams = sorted(set(played_df["home_team"].dropna()) | set(played_df["away_team"].dropna()))
    lines.append(f"Total: {len(teams)}")
    for t in teams:
        lines.append(f"- {t}")
    lines.append("")
    lines.append("## Valores faltantes por columna (partidos jugados)")
    na_counts = played_df.isna().sum()
    any_na = False
    for col, n in na_counts.items():
        if n:
            lines.append(f"- {col}: {n}")
            any_na = True
    if not any_na:
        lines.append("(ninguno)")
    lines.append("")
    lines.append("## Duplicados exactos removidos en el merge")
    lines.append(str(dupes))
    lines.append("")
    lines.append("## Nombres de equipo sin mapeo explícito (usados tal cual aparecen en crudo)")
    if unmapped_teams:
        for t in sorted(unmapped_teams):
            lines.append(f"- {t}")
    else:
        lines.append("(ninguno — todos los nombres crudos están en team_mapping.csv)")
    lines.append("")
    lines.append(f"## Filas sin resultado y con fecha pasada excluidas (snapshot obsoleto de footballcsv)")
    lines.append(str(stale_unplayed_n))
    lines.append("")
    lines.append("## Próximos partidos reales (sin resultado, fecha futura — usados para predicción)")
    lines.append(str(len(fixtures_df)))
    for _, r in fixtures_df.iterrows():
        lines.append(f"- {r['date'].date()}: {r['home_team']} vs {r['away_team']} (jornada {r['round']})")
    QUALITY_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    all_events = pd.read_csv(PROCESSED / "normalized_events.csv", parse_dates=["date"])

    unmapped_teams = set()
    known_normalized = set(pd.read_csv(TEAM_MAPPING_PATH)["normalized_name"])
    for col in ("home_team", "away_team"):
        raw_col = col + "_raw"
        mismatched = all_events[~all_events[col].isin(known_normalized) & all_events[col].notna()]
        for _, row in mismatched.iterrows():
            unmapped_teams.add(f"{row[raw_col]} -> {row[col]} (source={row['source']})")

    played = all_events.dropna(subset=["home_goals", "away_goals", "date"]).copy()
    before = len(played)
    played = played.drop_duplicates(subset=["date", "home_team", "away_team", "home_goals", "away_goals"])
    dupes_removed = before - len(played)

    played = played.sort_values("date").reset_index(drop=True)
    keep_cols = ["date", "season", "stage", "round", "is_playoff", "home_team", "away_team",
                 "home_goals", "away_goals", "home_ht_goals", "away_ht_goals", "source"]
    played[keep_cols].to_csv(PROCESSED / "matches_clean.csv", index=False)

    # "Upcoming" = no result recorded AND date is not in the past relative to
    # today. footballcsv is a stale historical snapshot: several of its rows
    # have blank scores simply because the scrape ran mid-season, not because
    # the match is genuinely upcoming — those must NOT be treated as fixtures
    # to predict (they are unplayed, undated-result rows from years ago).
    today = pd.Timestamp.now().normalize()
    no_result = all_events["home_goals"].isna() | all_events["away_goals"].isna()
    fixtures = all_events[no_result].dropna(subset=["date"]).copy()
    stale_unplayed = fixtures[fixtures["date"] < today]
    fixtures = fixtures[fixtures["date"] >= today].sort_values("date").reset_index(drop=True)
    fixtures[["date", "season", "round", "home_team", "away_team", "source"]].to_csv(
        PROCESSED / "fixtures_upcoming.csv", index=False
    )

    build_quality_report(played, unmapped_teams, dupes_removed, fixtures, len(stale_unplayed))

    print(f"Partidos jugados limpios: {len(played)}")
    print(f"Duplicados removidos: {dupes_removed}")
    print(f"Filas obsoletas excluidas (sin resultado, fecha pasada): {len(stale_unplayed)}")
    print(f"Próximos partidos detectados: {len(fixtures)}")
    print(f"Nombres sin mapeo explícito: {len(unmapped_teams)}")
    print(f"Guardado en {PROCESSED}")
    print(f"Reporte de calidad: {QUALITY_REPORT_PATH}")


if __name__ == "__main__":
    main()
