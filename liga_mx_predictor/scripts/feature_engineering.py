"""
Feature engineering para el pipeline de predicción de Liga MX.

Principio rector (anti-leakage): TODA feature de un partido en la fecha D
se calcula usando exclusivamente partidos con fecha < D del mismo equipo (o
del enfrentamiento directo). Se implementa con `.shift(1)` antes de cualquier
`rolling`/`expanding`, de modo que el propio partido nunca contribuye a sus
propias features.

Limitación de fuentes de datos (ver reports/DATA_SOURCES.md): ninguna de las
dos fuentes disponibles (footballcsv, TheSportsDB en su tier gratuito) incluye
tiros, tiros a puerta, posesión, corners, tarjetas, faltas ni xG. Por lo tanto
las features de ataque/defensa se construyen a partir de goles (el único dato
de rendimiento por partido disponible), no de esas variables — no se inventan.

Salida:
  data/processed/features.csv          -> una fila por partido jugado, con
                                           features pre-partido + variables
                                           objetivo (result, home_goals, away_goals)
  data/processed/features_fixtures.csv -> una fila por próximo partido, con
                                           las mismas features calculadas con
                                           el estado de cada equipo a la fecha
                                           de hoy (sin variable objetivo)

Uso:
    python scripts/feature_engineering.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models.elo import compute_elo_history, INITIAL_ELO  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

FORM_WINDOWS = [3, 5, 10]
VENUE_WINDOW = 5
H2H_WINDOWS = [5, 10]


def _long_format(matches):
    """One row per team per match (both home and away perspective)."""
    home = matches.rename(columns={
        "home_team": "team", "away_team": "opponent",
        "home_goals": "goals_for", "away_goals": "goals_against",
    }).copy()
    home["is_home"] = 1

    away = matches.rename(columns={
        "away_team": "team", "home_team": "opponent",
        "away_goals": "goals_for", "home_goals": "goals_against",
    }).copy()
    away["is_home"] = 0

    long_df = pd.concat([home, away], ignore_index=True, sort=False)
    long_df["win"] = (long_df["goals_for"] > long_df["goals_against"]).astype(int)
    long_df["draw"] = (long_df["goals_for"] == long_df["goals_against"]).astype(int)
    long_df["loss"] = (long_df["goals_for"] < long_df["goals_against"]).astype(int)
    long_df["points"] = long_df["win"] * 3 + long_df["draw"] * 1
    long_df = long_df.sort_values(["team", "date"]).reset_index(drop=True)
    return long_df


def _rolling_shifted(long_df, group_cols, col, window, agg="mean"):
    g = long_df.groupby(group_cols)[col]
    shifted = g.shift(1)
    roll = shifted.groupby([long_df[c] for c in group_cols]).rolling(window, min_periods=1).agg(agg)
    roll = roll.reset_index(level=list(range(len(group_cols))), drop=True)
    return roll.reindex(long_df.index)


def add_form_features(long_df):
    for w in FORM_WINDOWS:
        long_df[f"wins_last_{w}"] = _rolling_shifted(long_df, ["team"], "win", w, "sum")
        long_df[f"points_last_{w}"] = _rolling_shifted(long_df, ["team"], "points", w, "sum")
        long_df[f"goals_for_last_{w}"] = _rolling_shifted(long_df, ["team"], "goals_for", w, "sum")
        long_df[f"goals_against_last_{w}"] = _rolling_shifted(long_df, ["team"], "goals_against", w, "sum")
        long_df[f"goal_diff_last_{w}"] = long_df[f"goals_for_last_{w}"] - long_df[f"goals_against_last_{w}"]
        long_df[f"avg_goals_scored_last_{w}"] = _rolling_shifted(long_df, ["team"], "goals_for", w, "mean")
        long_df[f"avg_goals_conceded_last_{w}"] = _rolling_shifted(long_df, ["team"], "goals_against", w, "mean")
    # clean_sheet_rate needs a boolean series rolled, computed separately:
    long_df["_clean_sheet"] = (long_df["goals_against"] == 0).astype(int)
    for w in FORM_WINDOWS:
        long_df[f"clean_sheet_rate_last_{w}"] = _rolling_shifted(long_df, ["team"], "_clean_sheet", w, "mean")
    long_df.drop(columns=["_clean_sheet"], inplace=True)

    # matches played so far (for confidence weighting / min-sample checks)
    long_df["matches_played_so_far"] = long_df.groupby("team").cumcount()

    # rest days since last match (schedule congestion)
    long_df["prev_match_date"] = long_df.groupby("team")["date"].shift(1)
    long_df["days_since_last_match"] = (long_df["date"] - long_df["prev_match_date"]).dt.days
    return long_df


def add_venue_features(long_df):
    """Home-only stats attached to rows where is_home==1, away-only where is_home==0."""
    for venue, flag in (("home", 1), ("away", 0)):
        mask = long_df["is_home"] == flag
        sub = long_df[mask].sort_values(["team", "date"]).copy()
        sub[f"{venue}_win_rate"] = _rolling_shifted(sub, ["team"], "win", VENUE_WINDOW, "mean")
        sub[f"{venue}_goals"] = _rolling_shifted(sub, ["team"], "goals_for", VENUE_WINDOW, "mean")
        sub[f"{venue}_goals_conceded"] = _rolling_shifted(sub, ["team"], "goals_against", VENUE_WINDOW, "mean")
        for col in (f"{venue}_win_rate", f"{venue}_goals", f"{venue}_goals_conceded"):
            long_df.loc[mask, col] = sub[col]
    return long_df


def compute_h2h(matches):
    """
    Head-to-head features, computed strictly from meetings before the
    current match date, regardless of which side was home in prior meetings.
    Weighted toward recent meetings by simply using the most recent N.
    """
    matches = matches.sort_values("date").reset_index(drop=True)
    records = {}  # frozenset({teamA, teamB}) -> list of dicts (chronological)
    h2h_rows = []

    for _, row in matches.iterrows():
        home, away = row["home_team"], row["away_team"]
        key = tuple(sorted([home, away]))
        history = records.get(key, [])

        feat = {}
        for w in H2H_WINDOWS:
            recent = history[-w:]
            home_wins = sum(1 for m in recent if m["winner"] == home)
            away_wins = sum(1 for m in recent if m["winner"] == away)
            draws = sum(1 for m in recent if m["winner"] is None)
            goals_home = sum(m["goals"][home] for m in recent)
            goals_away = sum(m["goals"][away] for m in recent)
            feat[f"h2h_home_wins_last_{w}"] = home_wins
            feat[f"h2h_draws_last_{w}"] = draws
            feat[f"h2h_away_wins_last_{w}"] = away_wins
            feat[f"h2h_home_goals_last_{w}"] = goals_home
            feat[f"h2h_away_goals_last_{w}"] = goals_away
            feat[f"h2h_matches_last_{w}"] = len(recent)
        h2h_rows.append(feat)

        hg, ag = row["home_goals"], row["away_goals"]
        winner = home if hg > ag else (away if ag > hg else None)
        history.append({"winner": winner, "goals": {home: hg, away: ag}})
        records[key] = history

    h2h_df = pd.DataFrame(h2h_rows)
    return pd.concat([matches.reset_index(drop=True), h2h_df], axis=1)


def build_features(matches):
    matches = matches.sort_values("date").reset_index(drop=True)
    matches["match_id"] = matches.index

    # --- Elo (leakage-safe, pre-match ratings) ---
    matches_elo, final_ratings = compute_elo_history(matches)
    matches = matches.merge(
        matches_elo[["match_id", "home_elo_pre", "away_elo_pre", "elo_diff_pre"]],
        on="match_id", how="left"
    )

    # --- H2H ---
    matches = compute_h2h(matches)

    # --- Rolling form + venue splits (long format then pivot back) ---
    long_df = _long_format(matches[["match_id", "date", "home_team", "away_team", "home_goals", "away_goals"]])
    long_df = add_form_features(long_df)
    long_df = add_venue_features(long_df)

    feature_cols = [c for c in long_df.columns if c not in (
        "match_id", "date", "team", "opponent", "goals_for", "goals_against",
        "is_home", "win", "draw", "loss", "points", "prev_match_date"
    )]

    # venue-specific columns only make sense for the side they were computed
    # on: "home_win_rate/goals/goals_conceded" is populated only on is_home==1
    # rows (structurally NaN otherwise), so it's only meaningful for the home
    # team of the current match; symmetrically for "away_*" on away rows.
    away_context_cols = {"away_win_rate", "away_goals", "away_goals_conceded"}
    home_context_cols = {"home_win_rate", "home_goals", "home_goals_conceded"}
    home_side_cols = [c for c in feature_cols if c not in away_context_cols]
    away_side_cols = [c for c in feature_cols if c not in home_context_cols]

    venue_rename = {"home_win_rate": "venue_win_rate", "home_goals": "venue_goals",
                     "home_goals_conceded": "venue_goals_conceded",
                     "away_win_rate": "venue_win_rate", "away_goals": "venue_goals",
                     "away_goals_conceded": "venue_goals_conceded"}

    home_feats = long_df[long_df["is_home"] == 1][["match_id"] + home_side_cols].rename(columns=venue_rename)
    home_feats = home_feats.add_prefix("home_").rename(columns={"home_match_id": "match_id"})
    away_feats = long_df[long_df["is_home"] == 0][["match_id"] + away_side_cols].rename(columns=venue_rename)
    away_feats = away_feats.add_prefix("away_").rename(columns={"away_match_id": "match_id"})

    matches = matches.merge(home_feats, on="match_id", how="left")
    matches = matches.merge(away_feats, on="match_id", how="left")

    # --- Target variables ---
    matches["result"] = np.select(
        [matches["home_goals"] > matches["away_goals"], matches["home_goals"] == matches["away_goals"]],
        ["H", "D"], default="A"
    )
    matches["total_goals"] = matches["home_goals"] + matches["away_goals"]

    return matches, final_ratings, long_df


def build_fixture_features(fixtures, matches_long, final_elo_ratings, h2h_matches):
    """
    Same feature set as build_features, but for future fixtures: uses the
    most recent known rolling window / Elo rating for each team as of "now"
    instead of a per-match shift (there is no future match to shift from).
    """
    rows = []
    latest_by_team = {}
    for team, grp in matches_long.groupby("team"):
        latest_by_team[team] = grp.sort_values("date").iloc[-1]

    for _, fx in fixtures.iterrows():
        home, away = fx["home_team"], fx["away_team"]
        row = {"date": fx["date"], "season": fx["season"], "round": fx["round"],
               "home_team": home, "away_team": away}

        row["home_elo_pre"] = final_elo_ratings.get(home, INITIAL_ELO)
        row["away_elo_pre"] = final_elo_ratings.get(away, INITIAL_ELO)
        row["elo_diff_pre"] = row["home_elo_pre"] - row["away_elo_pre"]

        for side, team in (("home", home), ("away", away)):
            last_row = latest_by_team.get(team)
            for w in FORM_WINDOWS:
                for stat in ("wins_last", "points_last", "goals_for_last", "goals_against_last",
                             "goal_diff_last", "avg_goals_scored_last", "avg_goals_conceded_last",
                             "clean_sheet_rate_last"):
                    col = f"{stat}_{w}"
                    # the *next* value of this rolling stat (i.e. computed
                    # including the team's most recent completed match) is
                    # exactly what "as of today" should carry forward.
                    row[f"{side}_{col}"] = _next_rolling_value(matches_long, team, col, w)
            for stat in ("win_rate", "goals", "goals_conceded"):
                venue = "home" if side == "home" else "away"
                row[f"{side}_venue_{stat}"] = _latest_venue_value(matches_long, team, venue, stat)
            row[f"{side}_matches_played_so_far"] = (last_row["matches_played_so_far"] + 1) if last_row is not None else 0
            row[f"{side}_days_since_last_match"] = (
                (pd.Timestamp(fx["date"]) - last_row["date"]).days if last_row is not None else np.nan
            )

        # H2H as of "today": reuse compute_h2h logic on historical matches only
        key = tuple(sorted([home, away]))
        history = h2h_matches.get(key, [])
        for w in H2H_WINDOWS:
            recent = history[-w:]
            home_wins = sum(1 for m in recent if m["winner"] == home)
            away_wins = sum(1 for m in recent if m["winner"] == away)
            draws = sum(1 for m in recent if m["winner"] is None)
            goals_home = sum(m["goals"].get(home, 0) for m in recent)
            goals_away = sum(m["goals"].get(away, 0) for m in recent)
            row[f"h2h_home_wins_last_{w}"] = home_wins
            row[f"h2h_draws_last_{w}"] = draws
            row[f"h2h_away_wins_last_{w}"] = away_wins
            row[f"h2h_home_goals_last_{w}"] = goals_home
            row[f"h2h_away_goals_last_{w}"] = goals_away
            row[f"h2h_matches_last_{w}"] = len(recent)

        rows.append(row)

    return pd.DataFrame(rows)


def _next_rolling_value(matches_long, team, stat_col, window):
    """
    Recomputes a rolling stat "as of today" (last `window` matches including
    the most recently played one) for a future fixture — as opposed to the
    shift(1)-lagged column used for historical training rows, which
    intentionally excludes the current row's own match.
    """
    grp = matches_long[matches_long["team"] == team].sort_values("date")
    if grp.empty:
        return np.nan
    base_col = {
        "wins_last": ("win", "sum"), "points_last": ("points", "sum"),
        "goals_for_last": ("goals_for", "sum"), "goals_against_last": ("goals_against", "sum"),
        "avg_goals_scored_last": ("goals_for", "mean"), "avg_goals_conceded_last": ("goals_against", "mean"),
    }
    prefix = "_".join(stat_col.split("_")[:-2])  # strip trailing "_last_{w}"
    if prefix == "goal_diff_last":
        gf = grp["goals_for"].tail(window).sum()
        ga = grp["goals_against"].tail(window).sum()
        return gf - ga
    if prefix == "clean_sheet_rate_last":
        return (grp["goals_against"].tail(window) == 0).mean()
    if prefix not in base_col:
        return np.nan
    col, agg = base_col[prefix]
    tail = grp[col].tail(window)
    return tail.sum() if agg == "sum" else tail.mean()


def _latest_venue_value(matches_long, team, venue, stat):
    flag = 1 if venue == "home" else 0
    grp = matches_long[(matches_long["team"] == team) & (matches_long["is_home"] == flag)].sort_values("date")
    if grp.empty:
        return np.nan
    tail = grp.tail(VENUE_WINDOW)
    if stat == "win_rate":
        return tail["win"].mean()
    if stat == "goals":
        return tail["goals_for"].mean()
    if stat == "goals_conceded":
        return tail["goals_against"].mean()
    return np.nan


def build_h2h_index(matches):
    matches = matches.sort_values("date")
    records = {}
    for _, row in matches.iterrows():
        home, away = row["home_team"], row["away_team"]
        key = tuple(sorted([home, away]))
        hg, ag = row["home_goals"], row["away_goals"]
        winner = home if hg > ag else (away if ag > hg else None)
        records.setdefault(key, []).append({"winner": winner, "goals": {home: hg, away: ag}})
    return records


def main():
    matches = pd.read_csv(PROCESSED / "matches_clean.csv", parse_dates=["date"])
    fixtures = pd.read_csv(PROCESSED / "fixtures_upcoming.csv", parse_dates=["date"])

    features, final_ratings, matches_long = build_features(matches)
    features.to_csv(PROCESSED / "features.csv", index=False)
    print(f"features.csv: {features.shape[0]} partidos x {features.shape[1]} columnas")

    h2h_index = build_h2h_index(matches)
    fixture_features = build_fixture_features(fixtures, matches_long, final_ratings, h2h_index)
    fixture_features.to_csv(PROCESSED / "features_fixtures.csv", index=False)
    print(f"features_fixtures.csv: {fixture_features.shape[0]} próximos partidos x {fixture_features.shape[1]} columnas")


if __name__ == "__main__":
    main()
