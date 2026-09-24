"""
Validación temporal walk-forward (expanding window), obligatoria en vez de un
train/test split aleatorio: para cada temporada T (a partir de la segunda
temporada disponible), se entrena con TODAS las temporadas anteriores a T y
se predice T completa. La ventana de entrenamiento se desplaza hacia adelante
temporada por temporada.

IMPORTANTE — hueco de datos: no existe ninguna fuente disponible para la
temporada 2025-26 completa (ver reports/DATA_SOURCES.md); el histórico salta
de sep-2024 a jul-2026 (667 días). El fold de test "2026-2027" arranca por lo
tanto con features de forma reciente calculadas sobre partidos de hasta ~22
meses de antigüedad para muchos equipos — se reporta igualmente para no
descartar datos reales, pero se documenta la degradación esperada de señal
en reports/MODEL_ERROR_ANALYSIS.md.

Salida: data/processed/backtest_predictions.csv con, por partido de test:
  match_id, date, season, home_team, away_team, result (real),
  home_goals, away_goals,
  logistic_H/D/A, random_forest_H/D/A, gradient_boosting_H/D/A, poisson_H/D/A

Uso:
    python scripts/backtest.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models.feature_columns import get_feature_columns  # noqa: E402
from models.poisson import fit_poisson_model, predict_match  # noqa: E402
from models import logistic, random_forest, gradient_boosting  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

ML_MODELS = {
    logistic.MODEL_NAME: logistic.build_model,
    random_forest.MODEL_NAME: random_forest.build_model,
    gradient_boosting.MODEL_NAME: gradient_boosting.build_model,
}
CLASS_ORDER = ["A", "D", "H"]  # sklearn's alphabetical class ordering for H/D/A


def season_order(df):
    return (
        df.groupby("season")["date"].min().sort_values().index.tolist()
    )


def run_walk_forward(features_df, matches_df):
    seasons = season_order(features_df)
    feature_cols = get_feature_columns(features_df)
    all_predictions = []

    for i in range(1, len(seasons)):
        test_season = seasons[i]
        train_seasons = seasons[:i]

        train_df = features_df[features_df["season"].isin(train_seasons)]
        test_df = features_df[features_df["season"] == test_season]
        if train_df.empty or test_df.empty:
            continue

        X_train, y_train = train_df[feature_cols], train_df["result"]
        X_test = test_df[feature_cols]

        fold_preds = test_df[["match_id", "date", "season", "home_team", "away_team",
                               "result", "home_goals", "away_goals"]].copy()

        for model_name, builder in ML_MODELS.items():
            if y_train.nunique() < 2:
                continue
            pipe = builder()
            pipe.fit(X_train, y_train)
            proba = pipe.predict_proba(X_test)
            classes = list(pipe.named_steps["clf"].classes_) if "clf" in pipe.named_steps else list(pipe.classes_)
            for cls in CLASS_ORDER:
                col = f"{model_name}_{cls}"
                if cls in classes:
                    fold_preds[col] = proba[:, classes.index(cls)]
                else:
                    fold_preds[col] = 0.0

        train_matches = matches_df[matches_df["season"].isin(train_seasons)]
        poisson_fitted = fit_poisson_model(train_matches)
        poisson_H, poisson_D, poisson_A = [], [], []
        for _, row in test_df.iterrows():
            pred = predict_match(poisson_fitted, row["home_team"], row["away_team"])
            poisson_H.append(pred["home_win"])
            poisson_D.append(pred["draw"])
            poisson_A.append(pred["away_win"])
        fold_preds["poisson_H"] = poisson_H
        fold_preds["poisson_D"] = poisson_D
        fold_preds["poisson_A"] = poisson_A

        print(f"[backtest] train={train_seasons} -> test={test_season}: "
              f"{len(train_df)} train / {len(test_df)} test partidos")
        all_predictions.append(fold_preds)

    return pd.concat(all_predictions, ignore_index=True)


def main():
    features_df = pd.read_csv(PROCESSED / "features.csv", parse_dates=["date"])
    matches_df = pd.read_csv(PROCESSED / "matches_clean.csv", parse_dates=["date"])

    out = run_walk_forward(features_df, matches_df)
    out.to_csv(PROCESSED / "backtest_predictions.csv", index=False)
    print(f"\nTotal partidos evaluados fuera de muestra (walk-forward): {len(out)}")
    print(f"Guardado en {PROCESSED / 'backtest_predictions.csv'}")


if __name__ == "__main__":
    main()
