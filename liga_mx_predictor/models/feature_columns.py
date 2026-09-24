"""
Columnas de entrada (features) compartidas entre todos los modelos ML.

Se excluyen explícitamente identificadores, metadatos y cualquier columna
derivada del resultado del propio partido (leakage): home_goals, away_goals,
home_ht_goals, away_ht_goals, result, total_goals.
"""
NON_FEATURE_COLUMNS = {
    "match_id", "date", "season", "stage", "round", "is_playoff", "source",
    "home_team", "away_team",
    "home_goals", "away_goals", "home_ht_goals", "away_ht_goals",
    "result", "total_goals",
}


def get_feature_columns(df):
    return [c for c in df.columns if c not in NON_FEATURE_COLUMNS and df[c].dtype.kind in "if"]
