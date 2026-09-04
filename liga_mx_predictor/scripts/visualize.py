"""
Genera las visualizaciones del pipeline en reports/figures/:
  1. elo_trajectories.png       - evolución del rating ELO de los 6 equipos
                                   con mayor rating actual
  2. recent_form.png            - puntos en los últimos 5 partidos, equipos
                                   activos en la temporada 2026-2027
  3. goal_distribution.png      - distribución histórica de goles por partido
                                   vs. distribución implícita del modelo Poisson
  4. calibration_curve.png      - reliability diagram (antes/después de
                                   calibración isotónica)
  5. feature_importance.png     - importancia de features (Random Forest)
  6. predictions_chart.png      - probabilidades H/D/A de la próxima jornada
  7. historical_vs_predictions.png - frecuencia real de resultados vs.
                                   probabilidad promedio predicha (backtest)
  8. confusion_matrix.png       - matriz de confusión del ensemble calibrado
                                   sobre el backtest walk-forward

Uso:
    python scripts/visualize.py
"""
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import confusion_matrix  # noqa: E402

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models.elo import compute_elo_history  # noqa: E402
from models.poisson import fit_poisson_model, expected_goals, score_matrix  # noqa: E402
from scripts.predict import humanize_feature  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
ARTIFACTS = PROCESSED / "model_artifacts"
FIG_DIR = ROOT / "reports" / "figures"
PRED_DIR = ROOT / "predictions"

CLASS_ORDER = ["A", "D", "H"]
plt.rcParams["figure.dpi"] = 110


def plot_elo_trajectories(matches):
    hist, final_ratings = compute_elo_history(matches)
    top_teams = [t for t, _ in sorted(final_ratings.items(), key=lambda x: -x[1])[:6]]

    fig, ax = plt.subplots(figsize=(10, 6))
    for team in top_teams:
        team_rows = hist[(hist["home_team"] == team) | (hist["away_team"] == team)].copy()
        team_rows["elo"] = np.where(team_rows["home_team"] == team, team_rows["home_elo_pre"], team_rows["away_elo_pre"])
        ax.plot(team_rows["date"], team_rows["elo"], label=team, linewidth=1.5)
    ax.set_title("Evolución del rating ELO — 6 equipos con mayor rating actual")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Rating ELO")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "elo_trajectories.png")
    plt.close(fig)


def plot_recent_form(matches):
    recent_season = matches["season"].iloc[matches["date"].idxmax()]
    active_teams = sorted(set(matches[matches["season"] == recent_season]["home_team"]) |
                           set(matches[matches["season"] == recent_season]["away_team"]))

    long_home = matches.rename(columns={"home_team": "team", "home_goals": "gf", "away_goals": "ga"})
    long_away = matches.rename(columns={"away_team": "team", "away_goals": "gf", "home_goals": "ga"})
    long_home["points"] = np.where(long_home["gf"] > long_home["ga"], 3, np.where(long_home["gf"] == long_home["ga"], 1, 0))
    long_away["points"] = np.where(long_away["gf"] > long_away["ga"], 3, np.where(long_away["gf"] == long_away["ga"], 1, 0))
    long_df = pd.concat([
        long_home[["date", "team", "points"]], long_away[["date", "team", "points"]]
    ]).sort_values("date")

    points_last_5 = {}
    for team in active_teams:
        pts = long_df[long_df["team"] == team]["points"].tail(5)
        points_last_5[team] = pts.sum()

    series = pd.Series(points_last_5).sort_values()
    fig, ax = plt.subplots(figsize=(9, 7))
    colors = ["#c0392b" if v <= 4 else ("#f1c40f" if v <= 8 else "#27ae60") for v in series.values]
    ax.barh(series.index, series.values, color=colors)
    ax.set_title("Forma reciente — puntos en los últimos 5 partidos (equipos de la temporada más reciente)")
    ax.set_xlabel("Puntos (máx. 15)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "recent_form.png")
    plt.close(fig)


def plot_goal_distribution(matches):
    total_goals = matches["home_goals"] + matches["away_goals"]
    fitted = fit_poisson_model(matches)
    avg_home = matches["home_goals"].mean()
    avg_away = matches["away_goals"].mean()
    lam_home, lam_away = avg_home, avg_away
    matrix = score_matrix(lam_home, lam_away, max_goals=8)
    poisson_total = {g: 0.0 for g in range(17)}
    for i in range(9):
        for j in range(9):
            poisson_total[i + j] = poisson_total.get(i + j, 0) + matrix[i, j]

    fig, ax = plt.subplots(figsize=(9, 6))
    bins = np.arange(0, total_goals.max() + 2) - 0.5
    ax.hist(total_goals, bins=bins, density=True, alpha=0.6, label="Histórico real", color="#2980b9")
    xs = sorted(poisson_total.keys())
    ax.plot(xs, [poisson_total[x] for x in xs], "o-", color="#c0392b", label="Poisson (medias de liga)")
    ax.set_title("Distribución de goles totales por partido: histórico vs. modelo Poisson")
    ax.set_xlabel("Goles totales en el partido")
    ax.set_ylabel("Densidad / probabilidad")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "goal_distribution.png")
    plt.close(fig)


def plot_calibration_curve():
    calib = pd.read_csv(PROCESSED / "calibration_data.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), sharey=True)
    for ax, calibrated in zip(axes, [False, True]):
        suffix = "_calibrated" if calibrated else ""
        for cls, color in zip(CLASS_ORDER, ["#e74c3c", "#f1c40f", "#27ae60"]):
            sub = calib[calib["class"] == f"{cls}{suffix}"]
            if sub.empty:
                continue
            ax.plot(sub["predicted_mean"], sub["observed_freq"], "o-", color=color, label=f"Clase {cls}")
        ax.plot([0, 1], [0, 1], "--", color="gray", label="Calibración perfecta")
        ax.set_title("Sin calibrar" if not calibrated else "Calibrado (isotónica)")
        ax.set_xlabel("Probabilidad predicha (media del bin)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Frecuencia observada")
    axes[0].legend(fontsize=8)
    fig.suptitle("Reliability diagram — ensemble, walk-forward")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "calibration_curve.png")
    plt.close(fig)


def plot_feature_importance():
    feature_cols = joblib.load(ARTIFACTS / "feature_columns.joblib")
    rf = joblib.load(ARTIFACTS / "random_forest.joblib")
    importances = rf.named_steps["clf"].feature_importances_
    series = pd.Series(importances, index=feature_cols).sort_values(ascending=False).head(15)
    labels = [humanize_feature(c) for c in series.index]

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(labels[::-1], series.values[::-1], color="#8e44ad")
    ax.set_title("Importancia de features — Random Forest (top 15)")
    ax.set_xlabel("Importancia (Gini)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "feature_importance.png")
    plt.close(fig)


def plot_predictions_chart():
    preds = pd.read_csv(PRED_DIR / "current_predictions.csv")
    if preds.empty:
        return
    labels = [f"{r.home_team}\nvs {r.away_team}" for r in preds.itertuples()]
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(preds))
    width = 0.27
    ax.bar(x - width, preds["home_win_probability"], width, label="Home Win", color="#27ae60")
    ax.bar(x, preds["draw_probability"], width, label="Draw", color="#f1c40f")
    ax.bar(x + width, preds["away_win_probability"], width, label="Away Win", color="#c0392b")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Probabilidad")
    ax.set_title("Predicciones — próxima jornada")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "predictions_chart.png")
    plt.close(fig)


def plot_historical_vs_predictions():
    backtest = pd.read_csv(PROCESSED / "backtest_predictions.csv")
    weights = joblib.load(ARTIFACTS / "ensemble_weights.joblib")
    model_probs = {m: backtest[[f"{m}_{c}" for c in CLASS_ORDER]].to_numpy() for m in weights}
    combined = sum(w * model_probs[m] for m, w in weights.items())
    combined = combined / combined.sum(axis=1, keepdims=True)

    real_freq = backtest["result"].value_counts(normalize=True).reindex(CLASS_ORDER)
    predicted_avg = pd.Series(combined.mean(axis=0), index=CLASS_ORDER)

    fig, ax = plt.subplots(figsize=(7, 6))
    x = np.arange(3)
    width = 0.35
    ax.bar(x - width / 2, real_freq.values, width, label="Frecuencia real", color="#2980b9")
    ax.bar(x + width / 2, predicted_avg.values, width, label="Probabilidad media predicha", color="#e67e22")
    ax.set_xticks(x)
    ax.set_xticklabels(["Away Win", "Draw", "Home Win"])
    ax.set_ylabel("Proporción")
    ax.set_title("Resultados históricos vs. predicciones promedio (backtest walk-forward)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "historical_vs_predictions.png")
    plt.close(fig)


def plot_confusion_matrix():
    backtest = pd.read_csv(PROCESSED / "backtest_predictions.csv")
    weights = joblib.load(ARTIFACTS / "ensemble_weights.joblib")
    calibrators = joblib.load(ARTIFACTS / "calibrators.joblib")
    use_calibrated = joblib.load(ARTIFACTS / "calibration_flag.joblib")["use_calibrated"]

    model_probs = {m: backtest[[f"{m}_{c}" for c in CLASS_ORDER]].to_numpy() for m in weights}
    combined = sum(w * model_probs[m] for m, w in weights.items())
    combined = combined / combined.sum(axis=1, keepdims=True)
    if use_calibrated and calibrators is not None:
        combined = np.column_stack([calibrators[c].predict(combined[:, i]) for i, c in enumerate(CLASS_ORDER)])
        combined = combined / combined.sum(axis=1, keepdims=True)

    y_pred = [CLASS_ORDER[i] for i in np.argmax(combined, axis=1)]
    cm = confusion_matrix(backtest["result"], y_pred, labels=CLASS_ORDER)

    fig, ax = plt.subplots(figsize=(6, 5.5))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(3)); ax.set_xticklabels(CLASS_ORDER)
    ax.set_yticks(range(3)); ax.set_yticklabels(CLASS_ORDER)
    ax.set_xlabel("Predicción")
    ax.set_ylabel("Real")
    ax.set_title("Matriz de confusión — ensemble calibrado (backtest)")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "confusion_matrix.png")
    plt.close(fig)


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    matches = pd.read_csv(PROCESSED / "matches_clean.csv", parse_dates=["date"])

    plot_elo_trajectories(matches)
    plot_recent_form(matches)
    plot_goal_distribution(matches)
    plot_calibration_curve()
    plot_feature_importance()
    plot_predictions_chart()
    plot_historical_vs_predictions()
    plot_confusion_matrix()

    print(f"8 figuras guardadas en {FIG_DIR}")


if __name__ == "__main__":
    main()
