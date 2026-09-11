"""
Genera las predicciones finales para los próximos partidos de Liga MX.

Usa los modelos de PRODUCCIÓN entrenados por scripts/train.py sobre el
histórico completo (data/processed/model_artifacts/), las features
pre-calculadas de los próximos partidos (data/processed/features_fixtures.csv,
generadas por scripts/feature_engineering.py sin ningún dato posterior al
kickoff) y una simulación Monte Carlo (10,000 corridas) a partir de la matriz
de goles del modelo de Poisson (con corrección de Dixon-Coles) para obtener
la distribución de marcadores.

Por defecto predice únicamente la PRÓXIMA JORNADA real (la de fecha más
próxima en fixtures_upcoming.csv) — ver reports/DATA_SOURCES.md sobre la
limitación de TheSportsDB (solo 5 de los 9 partidos reales de cada jornada
están catalogados en la fuente gratuita).

Salida:
  predictions/current_predictions.csv
  predictions/current_predictions.md

Uso:
    python scripts/predict.py
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models.poisson import predict_match  # noqa: E402
from models import ensemble  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
ARTIFACTS = PROCESSED / "model_artifacts"
PRED_DIR = ROOT / "predictions"

CLASS_ORDER = ["A", "D", "H"]
N_SIMULATIONS = 10_000
CONSERVATIVE_THRESHOLD = 0.65
MODEL_VERSION = "liga-mx-predictor-v1.0 (2026-08-14)"

FEATURE_LABELS_ES = {
    "elo_pre": "rating ELO",
    "venue_win_rate": "% de victorias en su rol (local/visitante)",
    "venue_goals": "goles anotados en su rol (prom.)",
    "venue_goals_conceded": "goles recibidos en su rol (prom.)",
    "days_since_last_match": "días de descanso desde el último partido",
    "matches_played_so_far": "partidos jugados en el histórico disponible",
}
for w in (3, 5, 10):
    FEATURE_LABELS_ES[f"wins_last_{w}"] = f"victorias en los últimos {w} partidos"
    FEATURE_LABELS_ES[f"points_last_{w}"] = f"puntos en los últimos {w} partidos"
    FEATURE_LABELS_ES[f"goals_for_last_{w}"] = f"goles anotados en los últimos {w} partidos"
    FEATURE_LABELS_ES[f"goals_against_last_{w}"] = f"goles recibidos en los últimos {w} partidos"
    FEATURE_LABELS_ES[f"goal_diff_last_{w}"] = f"diferencia de goles en los últimos {w} partidos"
    FEATURE_LABELS_ES[f"avg_goals_scored_last_{w}"] = f"promedio de goles anotados (últimos {w})"
    FEATURE_LABELS_ES[f"avg_goals_conceded_last_{w}"] = f"promedio de goles recibidos (últimos {w})"
    FEATURE_LABELS_ES[f"clean_sheet_rate_last_{w}"] = f"% de partidos sin recibir gol (últimos {w})"
    FEATURE_LABELS_ES[f"h2h_home_wins_last_{w}"] = f"victorias del local en los últimos {w} enfrentamientos directos"
    FEATURE_LABELS_ES[f"h2h_away_wins_last_{w}"] = f"victorias del visitante en los últimos {w} enfrentamientos directos"
    FEATURE_LABELS_ES[f"h2h_home_goals_last_{w}"] = f"goles del local en los últimos {w} enfrentamientos directos"
    FEATURE_LABELS_ES[f"h2h_away_goals_last_{w}"] = f"goles del visitante en los últimos {w} enfrentamientos directos"
    FEATURE_LABELS_ES[f"h2h_draws_last_{w}"] = f"empates en los últimos {w} enfrentamientos directos"
    FEATURE_LABELS_ES[f"h2h_matches_last_{w}"] = f"enfrentamientos directos considerados (últimos {w})"


def humanize_feature(col):
    for side, side_label in (("home_", "local"), ("away_", "visitante")):
        if col.startswith(side):
            stripped = col[len(side):]
            label = FEATURE_LABELS_ES.get(stripped, stripped)
            return f"{label} ({side_label})"
    if col.startswith("h2h_"):
        stripped = col
        label = FEATURE_LABELS_ES.get(stripped, stripped)
        return f"{label} (H2H)"
    return col


def load_artifacts():
    feature_cols = joblib.load(ARTIFACTS / "feature_columns.joblib")
    models = {
        "logistic_regression": joblib.load(ARTIFACTS / "logistic_regression.joblib"),
        "random_forest": joblib.load(ARTIFACTS / "random_forest.joblib"),
        "gradient_boosting": joblib.load(ARTIFACTS / "gradient_boosting.joblib"),
    }
    poisson_fitted = joblib.load(ARTIFACTS / "poisson.joblib")
    weights = joblib.load(ARTIFACTS / "ensemble_weights.joblib")
    calibrators = joblib.load(ARTIFACTS / "calibrators.joblib")
    use_calibrated = joblib.load(ARTIFACTS / "calibration_flag.joblib")["use_calibrated"]
    return feature_cols, models, poisson_fitted, weights, calibrators, use_calibrated


def ensemble_probability(row, feature_cols, models, poisson_fitted, weights):
    X = pd.DataFrame([row[feature_cols].to_dict()])
    model_probs = {}
    for name, pipe in models.items():
        proba = pipe.predict_proba(X)[0]
        classes = list(pipe.named_steps["clf"].classes_)
        model_probs[name] = np.array([proba[classes.index(c)] if c in classes else 0.0 for c in CLASS_ORDER])

    poisson_pred = predict_match(poisson_fitted, row["home_team"], row["away_team"])
    model_probs["poisson"] = np.array([poisson_pred["away_win"], poisson_pred["draw"], poisson_pred["home_win"]])

    combined = sum(weights[m] * model_probs[m] for m in weights)
    combined = combined / combined.sum()
    return combined, poisson_pred, model_probs


def apply_calibration(proba, calibrators, use_calibrated):
    if not use_calibrated or calibrators is None:
        return ensemble.clip_and_renormalize(proba)
    calibrated = np.array([calibrators[c].predict([proba[i]])[0] for i, c in enumerate(CLASS_ORDER)])
    s = calibrated.sum()
    calibrated = calibrated / s if s > 0 else proba
    # Floor/ceiling: isotonic calibration can collapse to exactly 0 in
    # sparsely-populated probability bins (see MODEL_ERROR_ANALYSIS.md) —
    # football never has a truly impossible outcome.
    return ensemble.clip_and_renormalize(calibrated)


def monte_carlo_simulation(score_matrix, n_sims=N_SIMULATIONS, max_goals=8, seed=None):
    rng = np.random.default_rng(seed)
    flat = score_matrix.flatten()
    flat = flat / flat.sum()
    idx = rng.choice(len(flat), size=n_sims, p=flat)
    home_goals_sim = idx // (max_goals + 1)
    away_goals_sim = idx % (max_goals + 1)

    home_win_pct = (home_goals_sim > away_goals_sim).mean()
    draw_pct = (home_goals_sim == away_goals_sim).mean()
    away_win_pct = (home_goals_sim < away_goals_sim).mean()

    scorelines, counts = np.unique(
        np.stack([home_goals_sim, away_goals_sim], axis=1), axis=0, return_counts=True
    )
    order = np.argsort(-counts)
    top_scorelines = [
        {"score": f"{scorelines[o][0]}-{scorelines[o][1]}", "probability": counts[o] / n_sims}
        for o in order[:5]
    ]

    return {
        "home_win_pct": home_win_pct, "draw_pct": draw_pct, "away_win_pct": away_win_pct,
        "expected_home_goals": home_goals_sim.mean(), "expected_away_goals": away_goals_sim.mean(),
        "home_goals_ci90": (np.percentile(home_goals_sim, 5), np.percentile(home_goals_sim, 95)),
        "away_goals_ci90": (np.percentile(away_goals_sim, 5), np.percentile(away_goals_sim, 95)),
        "top_scorelines": top_scorelines,
    }


def top_factors(row, feature_cols, rf_pipe, top_k=10):
    importances = rf_pipe.named_steps["clf"].feature_importances_
    imp_series = pd.Series(importances, index=feature_cols).sort_values(ascending=False)

    favor_home, favor_away, neutral = [], [], []
    seen_pairs = set()
    for col in imp_series.index:
        if col.startswith("home_"):
            pair_col = "away_" + col[len("home_"):]
            side_a, side_b = col, pair_col
        elif col.startswith("h2h_home_"):
            pair_col = col.replace("h2h_home_", "h2h_away_", 1)
            side_a, side_b = col, pair_col
        else:
            continue
        pair_key = tuple(sorted([col, pair_col]))
        if pair_key in seen_pairs or pair_col not in feature_cols:
            continue
        seen_pairs.add(pair_key)

        val_a, val_b = row.get(side_a), row.get(side_b)
        if pd.isna(val_a) or pd.isna(val_b):
            continue
        label = humanize_feature(side_a if side_a.startswith("home_") or side_a.startswith("h2h_home_") else side_b)
        label = label.split(" (")[0]  # generic label without side annotation

        scale = max(abs(val_a), abs(val_b), 1e-6)
        rel_diff = (val_a - val_b) / scale
        if abs(rel_diff) < 0.08:
            neutral.append(label)
        elif rel_diff > 0:
            favor_home.append(label)
        else:
            favor_away.append(label)

        if len(favor_home) + len(favor_away) + len(neutral) >= top_k:
            break

    return favor_home[:5], favor_away[:5], neutral[:3]


def confidence_level(proba):
    sorted_p = np.sort(proba)[::-1]
    gap = sorted_p[0] - sorted_p[1]
    if gap < 0.08:
        return "Alta incertidumbre"
    if gap >= 0.20 and sorted_p[0] >= 0.50:
        return "Alta"
    return "Media"


def main():
    feature_cols, models, poisson_fitted, weights, calibrators, use_calibrated = load_artifacts()
    fixtures = pd.read_csv(PROCESSED / "features_fixtures.csv", parse_dates=["date"])

    if fixtures.empty:
        print("No hay próximos partidos disponibles en las fuentes de datos.")
        return

    next_round = fixtures.sort_values("date")["round"].iloc[0]
    to_predict = fixtures[fixtures["round"] == next_round].sort_values("date").reset_index(drop=True)
    print(f"Prediciendo jornada {next_round}: {len(to_predict)} partidos "
          f"(de un total de {len(fixtures)} próximos partidos disponibles en las fuentes).")

    rows_out = []
    md_blocks = []

    for _, row in to_predict.iterrows():
        proba_raw, poisson_pred, model_probs = ensemble_probability(row, feature_cols, models, poisson_fitted, weights)
        proba = apply_calibration(proba_raw, calibrators, use_calibrated)
        p_away, p_draw, p_home = proba  # CLASS_ORDER = A, D, H

        mc = monte_carlo_simulation(poisson_pred["score_matrix"], seed=hash((row["home_team"], row["away_team"])) % (2**32))
        conf = confidence_level(proba)
        favor_home, favor_away, neutral = top_factors(row, feature_cols, models["random_forest"])

        most_likely = mc["top_scorelines"][0]["score"]

        rows_out.append({
            "date": row["date"].date(), "home_team": row["home_team"], "away_team": row["away_team"],
            "home_win_probability": round(p_home, 4), "draw_probability": round(p_draw, 4),
            "away_win_probability": round(p_away, 4),
            "home_expected_goals": round(poisson_pred["lambda_home"], 3),
            "away_expected_goals": round(poisson_pred["lambda_away"], 3),
            "most_likely_score": most_likely, "confidence": conf, "model_version": MODEL_VERSION,
        })

        md_blocks.append({
            "row": row, "p_home": p_home, "p_draw": p_draw, "p_away": p_away,
            "poisson_pred": poisson_pred, "mc": mc, "conf": conf,
            "favor_home": favor_home, "favor_away": favor_away, "neutral": neutral,
            "most_likely": most_likely,
        })

    PRED_DIR.mkdir(parents=True, exist_ok=True)
    pred_df = pd.DataFrame(rows_out)
    pred_df.to_csv(PRED_DIR / "current_predictions.csv", index=False)

    write_markdown_report(md_blocks, next_round, len(fixtures))
    print(f"Guardado: {PRED_DIR / 'current_predictions.csv'} y current_predictions.md")


def write_markdown_report(blocks, round_no, total_fixtures_available):
    lines = ["# Predicciones — Liga MX", ""]
    lines.append(f"Jornada {round_no}. Modelo: {MODEL_VERSION}. "
                 f"Generado con datos disponibles hasta 2026-08-14.")
    lines.append("")
    lines.append("> Todas las probabilidades son estimaciones estadísticas de un modelo con incertidumbre "
                 "considerable (ver reports/MODEL_COMPARISON.md y MODEL_ERROR_ANALYSIS.md). Ningún resultado "
                 "está garantizado.")
    lines.append("")

    for b in blocks:
        row = b["row"]
        lines.append(f"## {row['home_team']} vs {row['away_team']}")
        lines.append(f"**Fecha:** {row['date'].date()}")
        lines.append("")
        lines.append(f"- Home Win: **{b['p_home']:.0%}**")
        lines.append(f"- Draw: **{b['p_draw']:.0%}**")
        lines.append(f"- Away Win: **{b['p_away']:.0%}**")
        lines.append("")
        lines.append(f"**Expected Goals:** {row['home_team']}: {b['poisson_pred']['lambda_home']:.2f} — "
                     f"{row['away_team']}: {b['poisson_pred']['lambda_away']:.2f}")
        lines.append(f"**Most likely score:** {b['most_likely']}")
        lines.append(f"**Confidence:** {b['conf']}")
        lines.append("")
        lines.append(f"**Simulación Monte Carlo ({N_SIMULATIONS:,} corridas):**")
        mc = b["mc"]
        lines.append(f"- Home {mc['home_win_pct']:.1%} / Draw {mc['draw_pct']:.1%} / Away {mc['away_win_pct']:.1%}")
        lines.append(f"- Goles esperados: {row['home_team']} {mc['expected_home_goals']:.2f} "
                     f"(IC90% {mc['home_goals_ci90'][0]:.0f}-{mc['home_goals_ci90'][1]:.0f}), "
                     f"{row['away_team']} {mc['expected_away_goals']:.2f} "
                     f"(IC90% {mc['away_goals_ci90'][0]:.0f}-{mc['away_goals_ci90'][1]:.0f})")
        lines.append("- Marcadores más probables: " + ", ".join(
            f"{s['score']} ({s['probability']:.1%})" for s in mc["top_scorelines"]
        ))
        lines.append(f"- Over 1.5: {b['poisson_pred']['over_1_5']:.0%} | Over 2.5: {b['poisson_pred']['over_2_5']:.0%} "
                     f"| Under 2.5: {b['poisson_pred']['under_2_5']:.0%} | Ambos anotan: {b['poisson_pred']['btts']:.0%}")
        lines.append("")
        lines.append("**Factores favorables al local:**")
        lines += [f"- {f}" for f in b["favor_home"]] or ["- (sin factores destacados)"]
        lines.append("**Factores favorables al visitante:**")
        lines += [f"- {f}" for f in b["favor_away"]] or ["- (sin factores destacados)"]
        if b["neutral"]:
            lines.append("**Factores neutrales:** " + ", ".join(b["neutral"]))
        lines.append("")
        lines.append("---")
        lines.append("")

    conservative = [b for b in blocks if max(b["p_home"], b["p_draw"], b["p_away"]) >= CONSERVATIVE_THRESHOLD]
    lines.append(f"## Predicción conservadora (probabilidad máxima ≥ {CONSERVATIVE_THRESHOLD:.0%})")
    if conservative:
        for b in conservative:
            row = b["row"]
            best = max([("Home", b["p_home"]), ("Draw", b["p_draw"]), ("Away", b["p_away"])], key=lambda x: x[1])
            lines.append(f"- {row['home_team']} vs {row['away_team']}: {best[0]} ({best[1]:.0%}) — "
                         f"el modelo estima una probabilidad de {best[1]:.0%}, no una certeza.")
    else:
        lines.append(f"Ningún partido de esta jornada alcanza el umbral de {CONSERVATIVE_THRESHOLD:.0%}. "
                     f"No se fuerzan picks: se devuelve una lista vacía.")
    lines.append("")

    def top1_minus_top2(b):
        sorted_p = sorted([b["p_home"], b["p_draw"], b["p_away"]], reverse=True)
        return sorted_p[0] - sorted_p[1]

    # Prioriza partidos que NO estén ya en la lista conservadora, para que
    # ambas listas aporten información distinta; si no alcanzan 3-4 partidos
    # sin solapamiento (jornadas muy chicas), se completa con el resto.
    def match_key(b):
        return (b["row"]["home_team"], b["row"]["away_team"])

    conservative_keys = {match_key(b) for b in conservative}
    non_conservative = [b for b in blocks if match_key(b) not in conservative_keys]
    risky = sorted(non_conservative, key=top1_minus_top2)
    if len(risky) < 3:
        risky_keys = {match_key(b) for b in risky}
        remaining = sorted([b for b in blocks if match_key(b) not in risky_keys], key=top1_minus_top2)
        risky += remaining
    risky = risky[:4]
    lines.append("## Predicción de riesgo / valor (partidos con situación estadística interesante)")
    for b in risky:
        row = b["row"]
        lines.append(f"- {row['home_team']} vs {row['away_team']}: H {b['p_home']:.0%} / D {b['p_draw']:.0%} / "
                     f"A {b['p_away']:.0%} — seleccionado por su reparto de probabilidades cerrado "
                     f"({b['conf']}), lo que implica que el modelo no encuentra un favorito claro y el "
                     f"resultado real puede aportar valor frente a un mercado que sí marque favorito.")
    lines.append("")
    lines.append(f"*Nota: solo {len(blocks)} de {total_fixtures_available} próximos partidos catalogados están "
                 f"disponibles para esta jornada por la limitación de la fuente gratuita TheSportsDB "
                 f"(ver reports/DATA_SOURCES.md) — no se completan los partidos faltantes con datos inventados.*")

    (PRED_DIR / "current_predictions.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
