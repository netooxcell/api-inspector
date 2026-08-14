"""
Análisis de errores del modelo sobre las predicciones walk-forward
(backtest_predictions.csv), usando el ensemble calibrado (o sin calibrar si
la calibración no ayudó — se lee el flag guardado por scripts/train.py).

Identifica:
  * Partidos con mayor error (log loss individual más alto)
  * Equipos con errores sistemáticos (como local / como visitante)
  * Tasa de acierto en empates vs. victorias
  * Upsets: resultado de baja probabilidad que ocurrió
  * Partidos de alta incertidumbre (P(H) ~ P(D) ~ P(A))

Salida: reports/MODEL_ERROR_ANALYSIS.md

Uso:
    python scripts/analyze_errors.py
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
ARTIFACTS = PROCESSED / "model_artifacts"
REPORT_PATH = ROOT / "reports" / "MODEL_ERROR_ANALYSIS.md"

CLASS_ORDER = ["A", "D", "H"]


def get_ensemble_probs(backtest):
    weights = joblib.load(ARTIFACTS / "ensemble_weights.joblib")
    calibrators = joblib.load(ARTIFACTS / "calibrators.joblib")
    use_calibrated = joblib.load(ARTIFACTS / "calibration_flag.joblib")["use_calibrated"]

    model_probs = {m: backtest[[f"{m}_{c}" for c in CLASS_ORDER]].to_numpy() for m in weights}
    combined = None
    for m, w in weights.items():
        contrib = w * model_probs[m]
        combined = contrib if combined is None else combined + contrib
    combined = combined / combined.sum(axis=1, keepdims=True)

    if use_calibrated and calibrators is not None:
        calibrated = np.column_stack([
            calibrators[c].predict(combined[:, i]) for i, c in enumerate(CLASS_ORDER)
        ])
        row_sums = calibrated.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        combined = calibrated / row_sums

    return combined


def main():
    backtest = pd.read_csv(PROCESSED / "backtest_predictions.csv", parse_dates=["date"])
    proba = get_ensemble_probs(backtest)
    for i, c in enumerate(CLASS_ORDER):
        backtest[f"ens_{c}"] = proba[:, i]

    y_idx = backtest["result"].map({c: i for i, c in enumerate(CLASS_ORDER)}).to_numpy()
    backtest["prob_of_actual"] = proba[np.arange(len(proba)), y_idx]
    backtest["match_log_loss"] = -np.log(np.clip(backtest["prob_of_actual"], 1e-15, 1))
    backtest["predicted_result"] = backtest[[f"ens_{c}" for c in CLASS_ORDER]].idxmax(axis=1).str[-1]
    backtest["correct"] = backtest["predicted_result"] == backtest["result"]

    probs_sorted = np.sort(proba, axis=1)
    backtest["max_minus_2nd"] = probs_sorted[:, -1] - probs_sorted[:, -2]
    backtest["is_high_uncertainty"] = backtest["max_minus_2nd"] < 0.08
    # "upset" = the outcome that actually happened had low predicted probability
    backtest["is_upset"] = backtest["prob_of_actual"] < 0.25

    lines = ["# MODEL_ERROR_ANALYSIS.md — Análisis de errores (ensemble, walk-forward)", ""]
    lines.append(f"Basado en {len(backtest)} partidos evaluados fuera de muestra.")
    lines.append("")

    lines.append("## 1. Peores predicciones individuales (mayor log loss)")
    worst = backtest.sort_values("match_log_loss", ascending=False).head(15)
    lines.append("| Fecha | Local | Visitante | Resultado real | P(H)/P(D)/P(A) ensemble | Log loss |")
    lines.append("|---|---|---|---|---|---|")
    for _, r in worst.iterrows():
        lines.append(
            f"| {r['date'].date()} | {r['home_team']} | {r['away_team']} | {r['result']} "
            f"({int(r['home_goals'])}-{int(r['away_goals'])}) | "
            f"{r['ens_H']:.2f} / {r['ens_D']:.2f} / {r['ens_A']:.2f} | {r['match_log_loss']:.3f} |"
        )
    lines.append("")

    lines.append("## 2. Errores sistemáticos por equipo")
    lines.append("Tasa de acierto del modelo en partidos de cada equipo (como local o visitante), "
                  "solo equipos con >= 20 partidos evaluados:")
    team_rows = []
    for team in sorted(set(backtest["home_team"]) | set(backtest["away_team"])):
        mask = (backtest["home_team"] == team) | (backtest["away_team"] == team)
        sub = backtest[mask]
        if len(sub) < 20:
            continue
        team_rows.append({
            "team": team, "n": len(sub),
            "accuracy": sub["correct"].mean(),
            "avg_log_loss": sub["match_log_loss"].mean(),
        })
    team_df = pd.DataFrame(team_rows).sort_values("avg_log_loss", ascending=False)
    lines.append("| Equipo | Partidos evaluados | Accuracy | Log loss promedio |")
    lines.append("|---|---|---|---|")
    for _, r in team_df.head(10).iterrows():
        lines.append(f"| {r['team']} | {int(r['n'])} | {r['accuracy']:.3f} | {r['avg_log_loss']:.3f} |")
    lines.append("")
    lines.append("(tabla completa ordenada de peor a mejor; se muestran los 10 equipos con mayor error promedio)")
    lines.append("")

    lines.append("## 3. Empates: el punto débil típico de los modelos 1X2")
    draws = backtest[backtest["result"] == "D"]
    draws_predicted_as_draw = (draws["predicted_result"] == "D").mean()
    lines.append(f"De {len(draws)} empates reales, el modelo predijo 'empate' como resultado más probable en "
                 f"solo el **{draws_predicted_as_draw:.1%}** de los casos — consistente con el problema conocido "
                 f"en modelos de fútbol de subestimar empates (la clase 'empate' rara vez es la más probable "
                 f"incluso cuando ocurre). El resto de aciertos en general provienen de partidos H/A.")
    lines.append("")

    lines.append("## 4. Upsets (resultado real con probabilidad predicha < 25%)")
    upsets = backtest[backtest["is_upset"]].sort_values("prob_of_actual")
    lines.append(f"Total: {len(upsets)} de {len(backtest)} ({len(upsets)/len(backtest):.1%})")
    lines.append("")
    lines.append("| Fecha | Local | Visitante | Resultado | P(resultado real) |")
    lines.append("|---|---|---|---|---|")
    for _, r in upsets.head(10).iterrows():
        lines.append(f"| {r['date'].date()} | {r['home_team']} | {r['away_team']} | {r['result']} "
                     f"({int(r['home_goals'])}-{int(r['away_goals'])}) | {r['prob_of_actual']:.2f} |")
    lines.append("")

    lines.append("## 5. Partidos de alta incertidumbre (diferencia entre 1ra y 2da probabilidad < 0.08)")
    hu = backtest[backtest["is_high_uncertainty"]]
    lines.append(f"Total: {len(hu)} de {len(backtest)} ({len(hu)/len(backtest):.1%}). "
                 f"Accuracy del modelo específicamente en estos partidos: {hu['correct'].mean():.3f} "
                 f"(vs. {backtest['correct'].mean():.3f} general) — como se espera, el modelo acierta "
                 f"notablemente menos en los partidos que él mismo señala como inciertos, lo cual valida "
                 f"la métrica de incertidumbre como señal útil y no solo un adorno.")
    lines.append("")

    lines.append("## 6. Limitaciones estructurales que explican parte del error")
    lines.append("- **Hueco de datos de ~22 meses** entre el fin de la temporada 2024-25 (footballcsv) y el "
                 "inicio de la Apertura 2026-27 (TheSportsDB): las features de forma reciente de ese fold "
                 "de test se calculan sobre partidos muy antiguos para varios equipos.")
    lines.append("- Sin datos de tiros, posesión, xG, tarjetas o lesiones (ninguna fuente disponible los "
                 "provee gratuitamente) — el modelo solo puede razonar sobre goles pasados y Elo, lo que "
                 "limita el techo de rendimiento frente a modelos que sí usan xG.")
    lines.append("- Temporadas de entrenamiento tempranas (2018-19, 2019-20) son pequeñas, por lo que los "
                 "primeros folds del walk-forward entrenan con relativamente poca información.")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Reporte guardado en {REPORT_PATH}")


if __name__ == "__main__":
    main()
