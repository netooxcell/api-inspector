"""
Limpieza y normalización (por fuente) de los datos crudos de Liga MX.

Entrada:  data/raw/footballcsv/*.csv, data/raw/thesportsdb/*.json
Salida:   data/processed/normalized_events.csv  (todas las fuentes, un esquema
          común, nombres de equipo normalizados; jugados y no jugados juntos —
          la combinación final, deduplicación y separación jugados/próximos
          ocurre en scripts/merge_data.py)

Decisiones de normalización relevantes (ver data/external/team_mapping.csv):
  * "Gallos Blancos" se mapea a "Querétaro" (es el mismo club, apodo distinto).
  * "Monarcas Morelia" y "Mazatlán FC" se mantienen como entidades separadas
    aunque la franquicia se reubicó de Morelia a Mazatlán en 2020: fusionarlas
    por similitud llevaría a mezclar planteles/rendimiento de ciudades y
    aficiones distintas bajo un mismo "equipo" para ELO/forma reciente, lo
    cual el enunciado pide evitar cuando existe riesgo de confusión.

Uso:
    python scripts/clean_data.py
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_FOOTBALLCSV = ROOT / "data" / "raw" / "footballcsv"
RAW_SPORTSDB = ROOT / "data" / "raw" / "thesportsdb"
RAW_MANUAL = ROOT / "data" / "raw" / "manual"
PROCESSED = ROOT / "data" / "processed"
TEAM_MAPPING_PATH = ROOT / "data" / "external" / "team_mapping.csv"

SCORE_RE = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")


def load_team_mapping():
    mapping_df = pd.read_csv(TEAM_MAPPING_PATH)
    lookup = dict(zip(mapping_df["original_name"], mapping_df["normalized_name"]))
    return lookup


def normalize_team(name, lookup):
    if pd.isna(name):
        return None
    name = str(name).strip()
    return lookup.get(name, name)  # fall back to raw name if unseen; flagged in quality report


def parse_score(raw):
    if pd.isna(raw):
        return None, None
    m = SCORE_RE.match(str(raw))
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def load_footballcsv(lookup):
    frames = []
    for path in sorted(RAW_FOOTBALLCSV.glob("*.csv")):
        season = path.stem
        df = pd.read_csv(path)
        df["season"] = season
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    raw = pd.concat(frames, ignore_index=True)

    raw["date"] = pd.to_datetime(raw["Date"], format="%a %b %d %Y", errors="coerce")
    home_goals, away_goals = zip(*raw["FT"].map(parse_score))
    home_ht, away_ht = zip(*raw["HT"].map(parse_score))

    out = pd.DataFrame({
        "date": raw["date"],
        "season": raw["season"],
        "stage": raw["Stage"],
        "round": raw["Round"],
        "is_playoff": raw["Stage"].astype(str).str.contains("Liguilla", case=False, na=False),
        "home_team_raw": raw["Team 1"],
        "away_team_raw": raw["Team 2"],
        "home_goals": home_goals,
        "away_goals": away_goals,
        "home_ht_goals": home_ht,
        "away_ht_goals": away_ht,
        "source": "footballcsv",
    })
    out["home_team"] = out["home_team_raw"].map(lambda n: normalize_team(n, lookup))
    out["away_team"] = out["away_team_raw"].map(lambda n: normalize_team(n, lookup))
    return out


def load_sportsdb_events(filename, lookup):
    path = RAW_SPORTSDB / filename
    if not path.exists():
        return pd.DataFrame()
    data = json.loads(path.read_text(encoding="utf-8"))
    events = data.get("events") or []
    rows = []
    for e in events:
        home_score = e.get("intHomeScore")
        away_score = e.get("intAwayScore")
        rows.append({
            "date": pd.to_datetime(e.get("dateEvent"), errors="coerce"),
            "season": e.get("strSeason"),
            "stage": None,
            "round": e.get("intRound"),
            "is_playoff": False,
            "home_team_raw": e.get("strHomeTeam"),
            "away_team_raw": e.get("strAwayTeam"),
            "home_goals": int(home_score) if home_score not in (None, "") else None,
            "away_goals": int(away_score) if away_score not in (None, "") else None,
            "home_ht_goals": None,
            "away_ht_goals": None,
            "source": "thesportsdb",
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["home_team"] = out["home_team_raw"].map(lambda n: normalize_team(n, lookup))
    out["away_team"] = out["away_team_raw"].map(lambda n: normalize_team(n, lookup))
    return out


def load_manual_fixtures(lookup):
    """
    Partidos confirmados manualmente por el usuario cuando no aparecen en
    ninguna fuente automática (ver data/raw/manual/README.md) — típicamente
    porque TheSportsDB (tier gratuito) solo cataloga 5 de los 9 partidos
    reales de cada jornada de Liga MX.
    """
    frames = []
    for path in sorted(RAW_MANUAL.glob("*.csv")):
        frames.append(pd.read_csv(path))
    if not frames:
        return pd.DataFrame()
    raw = pd.concat(frames, ignore_index=True)

    out = pd.DataFrame({
        "date": pd.to_datetime(raw["date"], errors="coerce"),
        "season": raw["season"].astype(str),
        "stage": None,
        "round": raw["round"],
        "is_playoff": False,
        "home_team_raw": raw["home_team"],
        "away_team_raw": raw["away_team"],
        "home_goals": None,
        "away_goals": None,
        "home_ht_goals": None,
        "away_ht_goals": None,
        "source": "manual_user_confirmed",
    })
    out["home_team"] = out["home_team_raw"].map(lambda n: normalize_team(n, lookup))
    out["away_team"] = out["away_team_raw"].map(lambda n: normalize_team(n, lookup))
    return out


def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    lookup = load_team_mapping()

    fcsv = load_footballcsv(lookup)
    sdb_past = load_sportsdb_events("past_events.json", lookup)
    sdb_next = load_sportsdb_events("next_events.json", lookup)
    sdb_rounds = load_sportsdb_events("current_season_rounds.json", lookup)
    manual = load_manual_fixtures(lookup)

    all_events = pd.concat([fcsv, sdb_past, sdb_next, sdb_rounds, manual], ignore_index=True, sort=False)
    # sdb_past/sdb_next are subsets of sdb_rounds's round range for the same
    # season (both draw from the same live current-season fixture list) —
    # drop exact duplicates on the natural key before anything else.
    all_events = all_events.drop_duplicates(
        subset=["date", "home_team_raw", "away_team_raw", "home_goals", "away_goals"]
    )
    all_events = all_events.sort_values("date").reset_index(drop=True)

    out_path = PROCESSED / "normalized_events.csv"
    all_events.to_csv(out_path, index=False)
    print(f"Eventos normalizados (jugados + programados, ambas fuentes): {len(all_events)}")
    print(f"Guardado en {out_path}")
    print("Ejecuta scripts/merge_data.py a continuación para combinar, deduplicar "
          "y separar en partidos jugados / próximos.")


if __name__ == "__main__":
    main()
